# Déclencher un publisher

Un publisher construit un message, il ne s'appelle pas tout seul. Ce qu'il faut écrire,
là où l'écriture vient de se faire :

```python
from rabbit_bus.emit import AmqpPublish

message = AmqpPublish("folder:POST")
message.pk = 630
message.execute()
```

`pk` est la seule chose obligatoire : c'est la ligne annoncée, nombre ou chaîne. Une
instance de modèle ou un dict conviennent aussi, seule leur PK part. Sans `pk`, rien
n'est envoyé et `execute()` retourne `False`.

`execute()` exécute le publisher sur place et envoie son message directement aux `QUEUES`
déclarées dans le fichier du namespace. La boîte du `.env` ne sert qu'aux consumers, rien
n'y transite ; elle est seulement inscrite en `replyTo` pour que les réponses reviennent
au bus. Rien ne bloque, rien ne lève.

## Les attributs

```python
message = AmqpPublish("folder:POST")
message.pk = 630
message.extra = {"origine": "create_folder", "par": request.user.pk, "exemple": "ce json tu mets ce que tu veux"}
message.files = []
message.execute()
```

| Attribut | Obligatoire | Ce qu'il porte                                                       |
| -------- | ----------- | -------------------------------------------------------------------- |
| `pk`     | oui         | la PK de la ligne annoncée                                           |
| `extra`  | non         | n'importe quel JSON, libre, à côté de la PK sans jamais s'y mélanger |
| `files`  | non         | liste de fichiers, vide pour l'instant                               |

Tout autre attribut posé sur l'objet part dans l'enveloppe sous son propre nom, c'est
ainsi qu'on ajoute un champ sans toucher au bus :

```python
message.source = "back-office"
```

Seul `args` est réservé : il porte `pk` et `extra`, et il est reconstruit à l'envoi.

## Le message qui part

Toujours cette forme, quel que soit le publisher :

```json
{
  "method": "POST",
  "table": "app_folder",
  "persist": false,
  "files": [],
  "replyTo": "gp1-local.queue",
  "correlationId": "c5dc4581-9480-4b9f-964e-d04a02cdf63a",
  "publishedAt": "2026-09-04T09:42:32.249Z",
  "args": { "pk": 3890, "extra": { "...": "ton objet" } }
}
```

| Namespace              | Ce qui est annoncé            |
| ---------------------- | ----------------------------- |
| `folder:POST`          | dossier propriétaire créé     |
| `rendu_dg:PATCH`       | état des lieux de sortie posé |
| `honoraires_edl:PATCH` | champ honoraires EDL modifié  |

`honoraires_edl:PATCH` part tout seul quand le consumer du même namespace réussit son
écriture. Ne jamais le publier à la main : cela n'annoncerait rien, cela exécuterait
l'écriture en base.

Après modification d'un fichier : `sudo systemctl restart gp1-test-bus`.

## Exemple réel : la création d'un dossier

Le `save()` de `Folder` dans `app/models.py`, avec les lignes ajoutées. L'appel se place
après le `super().save()` : avant, la PK n'existe pas encore. `creating` retient
l'information parce qu'après la sauvegarde, la ligne n'est plus reconnaissable comme
neuve, et il sert à n'annoncer que la création, puisque le namespace dit POST.

```python
from rabbit_bus.emit import AmqpPublish        # en haut du fichier


    def save(self, *args, **kwargs):
        if self.pk:
            previous = Folder.objects.get(pk=self.pk)
            step_changed = previous.step != self.step
        else:
            step_changed = False

        creating = not self.pk                  # ajout

        super().save(*args, **kwargs)

        if creating:                            # ajout
            message = AmqpPublish("folder:POST")
            message.pk = self.pk
            message.execute()

        if step_changed:
            self.create_notification()
            self.create_notification_admin()

        # la suite du save inchangée
```

Aucune des vingt créations de `Folder` dans `app/form.py` n'a besoin d'être touchée :
elles passent toutes par ce `save()`.

## L'ancienne forme

`emit("folder:POST", 630, {...})` fonctionne toujours, à l'identique : c'est la même
publication écrite en une ligne. Rien à changer dans le code déjà en place.
