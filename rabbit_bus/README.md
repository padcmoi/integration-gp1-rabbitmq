# rabbit_bus

Bus RabbitMQ autonome de GP1 test. Il écoute la file `gp1-test.queue` : un message
qui nomme un namespace connu exécute ce namespace, et la valeur retournée est
renvoyée à la file nommée dans `replyTo`.

Totalement à part : rien ici n'importe le code Django au démarrage, et le code
Django n'importe rien d'ici. Un consumer qui a besoin des données de l'app charge
Django dans le processus au premier appel (via `consumers/_django.py`), puis passe
par l'ORM de l'app, lectures comme écritures.

## Message accepté

```json
{
  "namespace": "honoraires_edl:GET",
  "replyTo": "la-file-qui-veut-la-reponse",
  "correlationId": "au-choix-de-l-emetteur",
  "args": { "pk": 542 }
}
```

`replyTo` et `correlationId` sont optionnels (acceptés aussi en propriétés AMQP
standard `reply_to` / `correlation_id`). Sans `replyTo`, l'exécution a lieu et le
résultat est seulement journalisé. L'enveloppe signée de la lib
`@naskot/node-rabbitmq-brokers` est acceptée telle quelle : son `type` est le
namespace, son `data` porte les args (et `replyTo` / `correlationId` dedans).

## Réponse envoyée

```json
{
  "namespace": "honoraires_edl:GET",
  "correlationId": "au-choix-de-l-emetteur",
  "ok": true,
  "result": { "id": 542, "honoraires_edl": { "...": "..." } }
}
```

Un échec est une réponse (`ok: false` + `error`), jamais un message rejoué en
boucle. Un namespace inconnu répond `ok: false` avec les namespaces connus
(consumers et publishers). Un message sans namespace (les événements d'écriture
du data-provider, par exemple) est journalisé puis acquitté.

## Consumers : un dossier métier, un fichier par verbe

```
consumers/
  _global/              namespaces globaux, un fichier chacun, NAMESPACE déclaré :
    ping.py             -> "ping"
    fais_moi_le_cafe.py -> "fais_moi_le_cafe"
  honoraires_edl/       un dossier par métier, nommé comme la route GP1 qu'il
    get.py              reflète (/honoraires_edl) :
    post.py             -> "honoraires_edl:GET", "honoraires_edl:POST", ...
    put.py
    patch.py
    delete.py
```

Règles, toutes vérifiées au démarrage (un fichier fautif est refusé avec une
erreur dans le journal, jamais enregistré en silence) :

- dans un dossier métier, **seuls** `get.py`, `post.py`, `put.py`, `patch.py`
  et `delete.py` sont autorisés ;
- chaque fichier déclare son `NAMESPACE`, et il doit valoir exactement
  `<dossier>:<VERBE en majuscules>` : le nom est visible dans le fichier et le
  chemin le garantit ;
- le nom du dossier métier reprend le slug de la route GP1 correspondante ;
  les noms réservés au bus commencent par `_` (aucune route GP1 ne commence
  par un underscore, la collision est impossible) : `_global/` pour les
  namespaces globaux, `_django.py` pour le helper ;
- chaque dossier contient un `__init__.py` vide.
- la logique métier d'un dossier vit dans son sous-dossier `business/`
  (`honoraires_edl/business/steps.py` pour le système de step,
  `WRITABLE_FIELDS` dans `business/__init__.py` pour le contrat d'écriture
  du PATCH : un champ = une ligne + son validateur). Un sous-dossier d'un
  dossier métier n'est jamais enregistré comme namespace.

Le modèle d'un consumer :

```python
from consumers._django import json_safe, setup_django

NAMESPACE = "honoraires_edl:GET"
ARGS = {"pk": 542}          # les arguments attendus, avec un exemple

def run(args):
    setup_django()          # seulement si les donnees de l app sont necessaires
    from app.models import HonorairesEDL
    ...
    return {"ce": "que la reponse contient"}
```

### L'enveloppe des verbes

Le verbe est dit par le namespace, `pk` dit le qui, `data` porte ce qui change :

| verbe       | args                          |
| ----------- | ----------------------------- |
| GET, DELETE | `{"pk": 425}`                 |
| POST        | `{"data": {...}}`             |
| PUT, PATCH  | `{"pk": 425, "data": {...}}`  |

Les écritures passent par l'instance du modèle et `save()` (voir
[honoraires_edl/patch.py](consumers/honoraires_edl/patch.py)), jamais par du
SQL direct : la logique métier des modèles s'applique comme si l'app avait
fait l'écriture elle-même. Un verbe pas encore implémenté lève
`NotImplementedError` et répond donc `ok: false` proprement.

## Publishers

Un fichier par publisher dans `publishers/`, avec **1 ou N queues de
destination**. Le modèle est
[publishers/publie_exemple.py](publishers/publie_exemple.py) :

```python
NAMESPACE = "publie_exemple"
QUEUES = ["test.queue", "autre.queue"]   # 1..N destinations
ARGS = {"demo": 1}

def run(args):
    return {"le": "message publie sur chaque queue"}
```

Déclenchement : un message entrant qui nomme ce namespace. Le bus publie alors
le retour de `run(args)` vers chaque queue listée, en **mode direct** RabbitMQ
(exchange par défaut `""`, routing key = nom exact de la queue : un message, un
destinataire). Le bus estampille `replyTo` (notre queue) et un `correlationId`
sur chaque publication : **les queues destinataires peuvent répondre**, et leurs
réponses, reconnues par le `correlationId`, sont enregistrées dans
`publish.txt` au lieu d'être traitées comme des commandes.

Celui qui a déclenché reçoit en réponse `{"ok": true, "published": {"queues":
[...], "correlationId": "..."}}`.

## HTTP_CODE et reason des réponses

Chaque réponse d'un consumer vers l'émetteur porte `HTTP_CODE` et `reason` :

| HTTP_CODE | reason                | quand                                                    |
| --------- | --------------------- | -------------------------------------------------------- |
| 200       | OK                    | GET/PUT/PATCH/DELETE réussi, global réussi               |
| 201       | Created               | POST réussi                                              |
| 202       | Accepted              | publisher déclenché, publications parties                |
| 400       | Bad Request           | valeur ou forme refusée (validation business, full_clean) |
| 403       | Forbidden             | règle business qui interdit l'opération (`Forbidden`)    |
| 404       | Not Found             | pk introuvable, ou namespace inconnu                     |
| 409       | Conflict              | déjà dans cet état (patcher step 1 quand il vaut 1)      |
| 500       | Internal Server Error | erreur inattendue                                        |
| 501       | Not Implemented       | verbe pas encore implémenté                              |

Il n'y a pas de 401 : la boîte aux lettres est l'autorisation, qui ne peut pas
publier sur la queue ne peut pas parler au bus. Côté consumer, on lève
`BadRequest` / `Forbidden` / `NotFound` / `Conflict` de `consumers/_errors.py` ;
un `ValueError` nu répond 400, `NotImplementedError` 501, le reste 500.

## Le consumer `namespaces`

Répond la liste de tout ce qui existe, avec les arguments attendus déclarés par
chaque fichier (`ARGS`) : c'est ce qui alimente le select et les champs
préremplis de l'app de test.

## Debug (optionnel)

`BUS_DEBUG=true` dans `rabbit_bus/.env` (activé). Le bus écrit alors, à côté de
`main.py`, une ligne JSON par événement :

| Fichier       | Contenu                                                                    |
| ------------- | -------------------------------------------------------------------------- |
| `consume.txt` | tout ce qui est consommé (commande, sans namespace, inconnu, illisible)    |
| `publish.txt` | chaque publication d'un publisher + les réponses reçues à ces publications |

Rotation automatique à 5 Mo (`.old`). `BUS_DEBUG=false` : plus aucune écriture.

## Ajouter / modifier

Déposer ou éditer le fichier, puis `sudo systemctl restart gp1-test-bus`.

## Exploitation

- service : `sudo systemctl status|start|stop|restart gp1-test-bus`
- console : `journalctl -u gp1-test-bus -f` ; même contenu dans
  `/var/log/gp1-test-bus/bus.log`
- identifiants + debug : `rabbit_bus/.env` (hors git, modèle dans `.env.sample`)
