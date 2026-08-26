# Mettre AI Choir Parts en ligne — pas à pas

Objectif : héberger l'app (une seule fois) pour l'installer ensuite sur les téléphones.
Tout se fait dans le navigateur, sans commande. Compte ~10 minutes.

Tu auras besoin de deux comptes gratuits : **GitHub** et **Render**.

---

## Étape 1 — Créer un compte GitHub
1. Va sur https://github.com → **Sign up**.
2. Suis les étapes (email, mot de passe, vérification).

## Étape 2 — Mettre le code sur GitHub
1. En haut à droite → **+** → **New repository**.
2. Repository name : `ai-choir-parts`. Laisse **Public**. Clique **Create repository**.
3. Sur la page qui s'affiche, clique le lien **« uploading an existing file »**.
4. **Décompresse** le fichier `ai-choir-parts.zip` sur ton ordinateur.
5. Ouvre le dossier décompressé, **sélectionne tout ce qu'il y a dedans**
   (les fichiers **et** les dossiers `templates` et `static`) et **glisse-les** dans la zone
   d'upload de GitHub.
6. En bas, clique **Commit changes**.

> Vérifie que tu vois bien, dans le dépôt, les fichiers `app.py`, `Dockerfile`, `render.yaml`,
> et les dossiers `templates/` et `static/`.

## Étape 3 — Créer un compte Render
1. Va sur https://render.com → **Get Started** → connecte-toi **avec GitHub** (le plus simple).
2. Autorise Render à accéder à tes dépôts.

## Étape 4 — Déployer
1. Sur Render : **New +** → **Blueprint**.
2. Choisis le dépôt `ai-choir-parts`. Render lit `render.yaml` tout seul.
3. Clique **Apply** / **Create**. Le build démarre (5–8 min : il installe le moteur audio).
4. Quand c'est **Live**, tu obtiens une adresse du type
   `https://ai-choir-parts.onrender.com`.

> Si Render demande un plan : choisis **Free**. (L'app s'endort après inactivité ; le 1er accès
> prend ~30 s, ensuite c'est fluide. Pour un usage intensif du groupe, le plus petit plan payant
> enlève ce délai.)

---

## Étape 5 — Installer sur le téléphone

### Android (Samsung)
1. Ouvre l'adresse `https://…onrender.com` dans **Chrome**.
2. Menu **⋮** → **Installer l'application** (ou **Ajouter à l'écran d'accueil**).
3. L'icône **AI Choir Parts** apparaît. Tu la lances comme une app.

*(Variante « vrai APK » : va sur https://www.pwabuilder.com, colle ton adresse, onglet Android →
Generate Package → tu télécharges un `.apk` à installer/partager.)*

### iPhone
1. Ouvre l'adresse dans **Safari** (important : Safari, pas Chrome).
2. Bouton **Partager** → **Sur l'écran d'accueil**.
3. L'icône apparaît et s'ouvre en plein écran.

---

## Étape 6 — Utiliser et partager
- Dans l'app : **🎤 Enregistrer ma voix** (chante a cappella) ou **importe** un fichier,
  choisis ton pupitre si besoin, **Générer les pupitres**, puis **⬇ MP3** sur chaque voix.
- Pour le groupe : envoie simplement l'adresse `https://…onrender.com` par WhatsApp.
  Chacun l'installe pareil sur son téléphone.

---

## En cas de souci
- Build qui échoue sur Render → ouvre l'onglet **Logs**, copie la dernière erreur.
- Page qui ne s'ouvre pas → attends 30 s (réveil du serveur gratuit) et recharge.
- Micro qui ne marche pas → autorise le micro dans le navigateur ; sur iPhone, utilise Safari.
