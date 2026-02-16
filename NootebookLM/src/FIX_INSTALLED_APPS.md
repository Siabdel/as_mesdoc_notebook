# 🔧 Fix : RuntimeError "Model class doesn't declare an explicit app_label"

## ❌ Erreur Rencontrée

```
RuntimeError: Model class apps.documents.models.SourceDocument doesn't 
declare an explicit app_label and isn't in an application in INSTALLED_APPS.
```

## 🎯 Cause

Django ne trouve pas vos apps dans `INSTALLED_APPS` parce que la configuration n'est pas correcte.

## ✅ Solution : 3 Étapes

---

### **Étape 1 : Vérifier la Structure des Apps**

Assurez-vous que chaque app a un fichier `apps.py` :

#### `apps/core/apps.py`
```python
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
```

#### `apps/documents/apps.py`
```python
from django.apps import AppConfig

class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.documents'
```

#### `apps/rag/apps.py`
```python
from django.apps import AppConfig

class RagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rag'
```

#### `apps/podcasts/apps.py`
```python
from django.apps import AppConfig

class PodcastsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.podcasts'
```

---

### **Étape 2 : Corriger INSTALLED_APPS**

Dans `config/settings.py`, remplacez la section `INSTALLED_APPS` par :

```python
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',  # IMPORTANT pour les tokens d'authentification
    'corsheaders',
    
    # Apps locales - NOTATION COMPLÈTE OBLIGATOIRE
    'apps.core.apps.CoreConfig',
    'apps.documents.apps.DocumentsConfig',
    'apps.rag.apps.RagConfig',
    'apps.podcasts.apps.PodcastsConfig',
]
```

**⚠️ IMPORTANT** : La notation complète `apps.xxx.apps.XxxConfig` est **obligatoire** quand vos apps sont dans un sous-dossier `apps/`.

---

### **Étape 3 : Vérifier que Tout Fonctionne**

```bash
# 1. Vérifier la configuration Django
python manage.py check

# Si vous voyez des erreurs de migration, c'est normal à ce stade

# 2. Créer les migrations
python manage.py makemigrations

# Vous devriez voir :
# - Create model SourceDocument
# - Create model DocumentChunk
# - Create model QueryLog

# 3. Appliquer les migrations
python manage.py migrate

# 4. Test final
python manage.py check --deploy
```

---

## 🔍 Vérifications Supplémentaires

### 1. Structure des Dossiers

Vérifiez que vous avez bien :

```
backend/
├── apps/
│   ├── __init__.py          ← Doit exister
│   ├── core/
│   │   ├── __init__.py      ← Doit exister
│   │   └── apps.py          ← Doit exister
│   ├── documents/
│   │   ├── __init__.py      ← Doit exister
│   │   ├── apps.py          ← Doit exister
│   │   └── models.py        ← Votre fichier
│   ├── rag/
│   │   ├── __init__.py      ← Doit exister
│   │   └── apps.py          ← Doit exister
│   └── podcasts/
│       ├── __init__.py      ← Doit exister
│       └── apps.py          ← Doit exister
└── config/
    ├── __init__.py          ← Doit exister
    └── settings.py          ← Votre configuration
```

### 2. Vérifier les Imports

Dans `apps/documents/models.py`, la première ligne devrait être :

```python
from django.db import models
```

Pas besoin de déclarer `app_label` manuellement si `INSTALLED_APPS` est correct.

### 3. Test d'Import Python

```bash
python manage.py shell
```

```python
# Test 1 : Importer l'app config
>>> from apps.documents.apps import DocumentsConfig
>>> print(DocumentsConfig.name)
apps.documents

# Test 2 : Importer le modèle
>>> from apps.documents.models import SourceDocument
>>> print(SourceDocument._meta.app_label)
documents

# Si ça passe, c'est bon ! ✅
```

---

## 📝 Checklist Complète

- [ ] Fichiers `apps.py` créés dans chaque app
- [ ] Tous les `__init__.py` présents
- [ ] `INSTALLED_APPS` utilise la notation complète `apps.xxx.apps.XxxConfig`
- [ ] `rest_framework.authtoken` ajouté dans `INSTALLED_APPS`
- [ ] `python manage.py check` ne retourne aucune erreur critique
- [ ] Migrations créées avec `makemigrations`
- [ ] Migrations appliquées avec `migrate`

---

## 🚀 Fichier Corrigé Disponible

Un fichier `django_settings_fixed.py` a été généré avec la configuration correcte.

**Pour l'utiliser** :

```bash
cd backend
cp config/settings.py config/settings.py.backup  # Sauvegarde
cp django_settings_fixed.py config/settings.py   # Remplace
python manage.py check  # Vérifier
```

---

## ⚡ Script de Vérification Rapide

Créez `check_setup.py` dans le dossier `backend/` :

```python
#!/usr/bin/env python
import os
import sys

def check_file_exists(path, name):
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {name}: {path}")
    return exists

def main():
    print("🔍 Vérification de la structure Django...\n")
    
    all_good = True
    
    # Vérifier les __init__.py
    all_good &= check_file_exists("apps/__init__.py", "__init__.py apps/")
    all_good &= check_file_exists("apps/core/__init__.py", "__init__.py core/")
    all_good &= check_file_exists("apps/documents/__init__.py", "__init__.py documents/")
    all_good &= check_file_exists("apps/rag/__init__.py", "__init__.py rag/")
    all_good &= check_file_exists("apps/podcasts/__init__.py", "__init__.py podcasts/")
    
    print()
    
    # Vérifier les apps.py
    all_good &= check_file_exists("apps/core/apps.py", "apps.py core/")
    all_good &= check_file_exists("apps/documents/apps.py", "apps.py documents/")
    all_good &= check_file_exists("apps/rag/apps.py", "apps.py rag/")
    all_good &= check_file_exists("apps/podcasts/apps.py", "apps.py podcasts/")
    
    print()
    
    # Vérifier config
    all_good &= check_file_exists("config/__init__.py", "__init__.py config/")
    all_good &= check_file_exists("config/settings.py", "settings.py")
    all_good &= check_file_exists("manage.py", "manage.py")
    
    print()
    
    if all_good:
        print("🎉 Tous les fichiers nécessaires sont présents !")
        print("\n📋 Prochaines étapes :")
        print("   1. python manage.py check")
        print("   2. python manage.py makemigrations")
        print("   3. python manage.py migrate")
    else:
        print("❌ Certains fichiers manquent. Utilisez setup_structure.sh pour les créer.")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

Exécutez-le :

```bash
cd backend
python check_setup.py
```

---

## 💡 Pourquoi cette Erreur ?

Django a besoin de savoir dans quelle "application" se trouve chaque modèle. Quand vous déclarez un modèle, Django :

1. Cherche dans `INSTALLED_APPS`
2. Trouve l'app qui correspond
3. Enregistre le modèle avec son `app_label`

Si l'app n'est pas dans `INSTALLED_APPS`, Django ne peut pas enregistrer le modèle → RuntimeError.

**Solution** : Toujours déclarer les apps dans `INSTALLED_APPS` avec la notation complète `'apps.nom_app.apps.NomAppConfig'`.

---

## 🆘 Toujours Bloqué ?

Si l'erreur persiste après ces corrections :

1. **Supprimez le cache Python** :
   ```bash
   find . -type d -name __pycache__ -exec rm -r {} +
   find . -type f -name "*.pyc" -delete
   ```

2. **Vérifiez les permissions** :
   ```bash
   chmod -R 755 apps/
   ```

3. **Redémarrez le serveur Django** :
   ```bash
   pkill -f "manage.py runserver"
   python manage.py runserver
   ```

4. **Vérifiez votre PYTHONPATH** :
   ```bash
   echo $PYTHONPATH
   # Devrait être vide ou pointer vers votre projet
   ```

---

Appliquez ces corrections et l'erreur devrait disparaître ! 🚀
