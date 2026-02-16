# 🎨 Smart-Notebook - Interface d'Administration Django

## 📋 Fichiers Créés

**`documents_admin.py`** - Interface d'administration complète pour :
- SourceDocument (documents uploadés)
- DocumentChunk (chunks vectorisés)
- QueryLog (historique des questions RAG)

---

## 🚀 Installation

### 1. Placer le fichier admin.py

```bash
# Copier le fichier dans l'app documents
cp documents_admin.py backend/apps/documents/admin.py
```

### 2. Créer un superutilisateur (si pas déjà fait)

```bash
cd backend
source venv/bin/activate
python manage.py createsuperuser

# Suivez les instructions :
# Username: admin
# Email: admin@smartnotebook.local
# Password: ******** (minimum 8 caractères)
```

### 3. Démarrer le serveur

```bash
python manage.py runserver
```

### 4. Accéder à l'admin

Ouvrez votre navigateur : **http://localhost:8000/admin**

---

## 🎯 Fonctionnalités de l'Interface Admin

### **1. Gestion des Documents (SourceDocument)**

#### Affichage dans la liste :
- ✅ **Icône selon le type** (📕 PDF, 📝 TXT)
- ✅ **Badge coloré du statut** (Pending, Processing, Completed, Failed)
- ✅ **Barre de progression visuelle**
- ✅ **Taille du fichier en format lisible** (KB, MB, GB)
- ✅ **Nombre de chunks** avec lien direct
- ✅ **Actions rapides** (Télécharger, Réessayer)

#### Filtres disponibles :
- Par statut de traitement
- Par type de fichier
- Par date de création
- Par utilisateur

#### Recherche :
- Par titre du document
- Par nom d'utilisateur
- Par hash du fichier

#### Actions groupées :
- 🔄 **Retraiter les documents** : Relance le traitement Celery
- 🗑️ **Supprimer les chunks** : Supprime tous les chunks associés
- ❌ **Marquer comme échoué** : Change le statut en FAILED

#### Page de détail :
- Aperçu du fichier avec lien de téléchargement
- Métadonnées extraites (auteur, date, etc.)
- **Inline des chunks** : Voir tous les chunks dans la même page
- Statistiques : pages, chunks, caractères

---

### **2. Gestion des Chunks (DocumentChunk)**

#### Affichage dans la liste :
- ✅ **Aperçu du contenu** (80 premiers caractères)
- ✅ **Lien vers le document parent**
- ✅ **Index du chunk** dans la séquence
- ✅ **Numéro de page** d'origine
- ✅ **Badge de longueur** (vert si < 500 chars)

#### Filtres :
- Par document source
- Par numéro de page
- Par date de création

#### Recherche :
- Dans le contenu des chunks
- Par titre du document
- Par nom d'utilisateur

#### Aperçu de l'embedding :
- Visualisation des 200 premiers caractères du vecteur
- Affichage dans un bloc code formaté

#### Restrictions :
- **Pas d'ajout manuel** : Les chunks sont créés automatiquement par Celery
- **Lecture seule** : Empêche la modification accidentelle

---

### **3. Logs des Requêtes RAG (QueryLog)**

#### Affichage dans la liste :
- ✅ **Question de l'utilisateur** (aperçu)
- ✅ **Nombre de documents consultés**
- ✅ **Badge du nombre de chunks** récupérés
- ✅ **Temps de réponse** (badge coloré selon la rapidité)
- ✅ **Tokens utilisés** (badge violet)
- ✅ **Note en étoiles** (⭐⭐⭐⭐⭐)

#### Filtres :
- Par utilisateur
- Par note (1-5 étoiles)
- Par date
- Par nombre de chunks récupérés

#### Recherche :
- Dans les questions
- Dans les réponses
- Par nom d'utilisateur

#### Page de détail :
- **Question complète**
- **Réponse complète** (zone scrollable)
- **Documents consultés** (sélection multiple)
- **Métriques** : temps, tokens, chunks

#### Restrictions :
- **Pas d'ajout manuel** : Les logs sont créés automatiquement
- **Lecture seule** : Préserve l'historique authentique

---

## 🎨 Personnalisation Visuelle

### Badges Colorés

L'interface utilise des badges colorés pour une lecture rapide :

| Couleur | Utilisation | Exemple |
|---------|-------------|---------|
| 🟡 Jaune (#f39c12) | Pending | Documents en attente |
| 🔵 Bleu (#3498db) | Processing | Traitement en cours |
| 🟢 Vert (#2ecc71) | Completed | Traitement réussi |
| 🔴 Rouge (#e74c3c) | Failed | Échec du traitement |
| 🟣 Violet (#9b59b6) | Tokens | Consommation de tokens |

### Icônes

- 📕 PDF
- 📝 TXT
- ⏳ Pending
- ⚙️ Processing
- ✅ Completed
- ❌ Failed
- 🔄 Retry
- 📥 Download
- ⭐ Rating

---

## 📊 Statistiques Globales

En haut de la liste des documents, vous verrez :

```
Total : 42 documents
En attente : 3
En traitement : 1
Complétés : 36
Échoués : 2
```

---

## 🔧 Actions Personnalisées Détaillées

### Retraiter les Documents

**Usage** :
1. Sélectionnez les documents en échec
2. Menu déroulant "Action" → "Retraiter les documents sélectionnés"
3. Cliquez sur "Exécuter"

**Effet** :
- Relance une tâche Celery pour chaque document
- Les anciens chunks sont supprimés automatiquement
- Le statut passe à PENDING puis PROCESSING

### Supprimer les Chunks

**Usage** :
1. Sélectionnez les documents
2. Action → "Supprimer les chunks"
3. Confirmer

**Effet** :
- Supprime tous les DocumentChunk associés
- Libère de l'espace dans la base de données
- Le document reste accessible mais non interrogeable en RAG

### Marquer comme Échoué

**Usage** :
- Pour marquer manuellement un document problématique
- Utile pour déboguer ou réorganiser

---

## 🔍 Exemples d'Utilisation

### Trouver tous les PDF traités avec succès

1. Allez dans **Documents**
2. Filtre : **Processing status** → Completed
3. Filtre : **File type** → application/pdf

### Voir les questions avec mauvaises notes

1. Allez dans **Query logs**
2. Filtre : **User rating** → 1 ou 2

### Retraiter tous les documents échoués

1. Allez dans **Documents**
2. Filtre : **Processing status** → Failed
3. Sélectionnez tous (Ctrl+A ou checkbox en haut)
4. Action → "Retraiter les documents"
5. Exécuter

### Analyser les temps de réponse

1. Allez dans **Query logs**
2. Triez par "Response time" (cliquez sur le header)
3. Identifiez les requêtes lentes (> 5 secondes)

---

## 🎓 Astuces d'Utilisation

### 1. Inline Editing des Chunks

Dans la page de détail d'un document, vous pouvez voir **tous les chunks** sans naviguer ailleurs :
- Cliquez sur un document → Section "Chunks" en bas
- Affichage tabulaire avec aperçu du contenu

### 2. Recherche Multi-critères

Combinez filtres et recherche :
- Filtre : User = "john"
- Recherche : "machine learning"
- Résultat : Toutes les questions de John sur le machine learning

### 3. Export de Données

Django Admin permet l'export CSV/JSON natif :
- Sélectionnez les items
- Action → "Export selected items"
- Choisir le format

### 4. Navigation Rapide

Les liens colorés sont cliquables :
- Cliquez sur le nombre de chunks → Liste filtrée
- Cliquez sur le nom du document → Page de détail
- Cliquez sur "Télécharger" → Fichier original

---

## 🛠️ Personnalisation Avancée

### Ajouter des filtres personnalisés

Éditez `documents_admin.py` :

```python
class YearListFilter(admin.SimpleListFilter):
    title = 'année'
    parameter_name = 'year'
    
    def lookups(self, request, model_admin):
        return (
            ('2024', '2024'),
            ('2025', '2025'),
        )
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(created_at__year=self.value())

# Puis dans SourceDocumentAdmin :
list_filter = (..., YearListFilter)
```

### Modifier les couleurs

Changez les valeurs hexadécimales dans les méthodes comme `status_badge()` :

```python
colors = {
    'COMPLETED': '#custom_green',  # Votre couleur
}
```

---

## 🐛 Dépannage

### L'admin ne s'affiche pas

**Vérifiez** :
```bash
# L'app est dans INSTALLED_APPS
grep "django.contrib.admin" config/settings.py

# Les URLs admin sont configurées
grep "admin.site.urls" config/urls.py
```

### Les badges ne s'affichent pas

**Cause** : Problème de HTML/CSS

**Solution** :
- Vérifiez que `format_html` est importé
- Testez avec un navigateur moderne (Chrome, Firefox)

### Actions ne fonctionnent pas

**Cause** : Celery non démarré

**Solution** :
```bash
# Vérifier que Celery tourne
ps aux | grep celery

# Relancer si nécessaire
celery -A config worker --loglevel=info
```

---

## 📈 Analytics avec l'Admin

### Questions fréquentes

```sql
SELECT query_text, COUNT(*) as count
FROM query_logs
GROUP BY query_text
ORDER BY count DESC
LIMIT 10;
```

Ou dans l'admin :
- Allez dans Query logs
- Recherchez manuellement les patterns

### Documents les plus utilisés

Dans l'admin, pas de SQL direct, mais :
1. Notez les documents cités fréquemment dans Query logs
2. Analysez les patterns d'utilisation

---

## 🎉 Résumé des Avantages

✅ **Interface riche et visuelle** : Badges, couleurs, icônes  
✅ **Actions groupées efficaces** : Retraiter, supprimer en masse  
✅ **Filtres puissants** : Trouvez rapidement ce que vous cherchez  
✅ **Lecture intuitive** : Aperçus, liens, statistiques  
✅ **Protection des données** : Pas d'ajout/modification accidentelle  
✅ **Monitoring en temps réel** : Statuts, progressions, métriques  

---

## 📞 Prochaines Étapes

1. **Accédez à l'admin** : http://localhost:8000/admin
2. **Uploadez un document** via l'interface frontend
3. **Observez le traitement** dans l'admin (refresh la page)
4. **Posez une question** via le chat RAG
5. **Consultez le log** dans Query logs

---

**Profitez de votre interface d'administration Smart-Notebook ! 🚀**
