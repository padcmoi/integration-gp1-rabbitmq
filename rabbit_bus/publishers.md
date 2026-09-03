# Déclencher un publisher

Un publisher construit un message, il ne s'appelle pas tout seul. La ligne à écrire, là
où l'écriture vient de se faire :

```python
from rabbit_bus.emit import emit

emit("folder:POST", instance)
```

`emit` exécute le publisher sur place et envoie son message directement aux `QUEUES`
déclarées dans le fichier du namespace, `gp1-data-provider.queue` et `test.queue`. La
boîte du `.env` ne sert qu'aux consumers, rien n'y transite ; elle est seulement
inscrite en `replyTo` pour que les réponses reviennent au bus.

Le publisher reçoit deux clés, jamais plus :

```json
{ "pk": 207, "extra": {} }
```

Le deuxième argument est la ligne annoncée. Seule sa PK part, nombre ou chaîne : une
instance, un dict ou la clé nue donnent le même message, les colonnes du modèle ne sont
jamais lues. Qui veut la ligne entière la relit à la source. Sans PK, rien ne part et
`emit` retourne `False`.

Le troisième argument, `extra`, est optionnel et totalement libre : n'importe quel JSON,
ce que tu veux dedans, transporté à côté de la PK sans jamais s'y mélanger. L'omettre est
une annonce complète, le mettre n'enlève rien.

```python
emit("folder:POST", 630)
emit("folder:POST", 630, {"origine": "create_folder", "par": request.user.pk, "exemple": "ce json tu mets ce que tu veux"})
```

`emit` ne bloque pas et ne lève jamais.

| Namespace              | La ligne                         | Ce qui est annoncé            |
| ---------------------- | -------------------------------- | ----------------------------- |
| `folder:POST`          | `emit("folder:POST", 630)`       | dossier propriétaire créé     |
| `rendu_dg:PATCH`       | `emit("rendu_dg:PATCH", 1)`      | état des lieux de sortie posé |
| `honoraires_edl:PATCH` | rien à écrire, c'est automatique | champ honoraires EDL modifié  |

`honoraires_edl:PATCH` part tout seul quand le consumer du même namespace réussit son
écriture. Ne jamais l'appeler avec `emit` : cela n'annoncerait rien, cela exécuterait
l'écriture en base.

Après modification d'un fichier : `sudo systemctl restart gp1-test-bus`.

## Exemple réel : la création d'un dossier

Le `save()` de `Folder` dans `app/models.py`, avec les deux lignes ajoutées. L'appel se
place après le `super().save()` : avant, la PK n'existe pas encore. `creating` retient
l'information parce qu'après la sauvegarde, la ligne n'est plus reconnaissable comme
neuve, et il sert à n'annoncer que la création, puisque le namespace dit POST.

```python
from rabbit_bus.emit import emit                   # en haut du fichier


    def save(self, *args, **kwargs):
        if self.pk:
            previous = Folder.objects.get(pk=self.pk)
            step_changed = previous.step != self.step
        else:
            step_changed = False

        creating = not self.pk                      # ajout

        super().save(*args, **kwargs)

        if creating:
            emit("folder:POST", self)               # ajout

        if step_changed:
            self.create_notification()
            self.create_notification_admin()

        # la suite du save inchangée
```

Aucune des vingt créations de `Folder` dans `app/form.py` n'a besoin d'être touchée :
elles passent toutes par ce `save()`.
