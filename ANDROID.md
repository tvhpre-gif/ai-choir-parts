# Installer AI Choir Parts sur ton Samsung Android

Pas de `.apk` livré tout fait : le moteur audio (pyworld, librosa, ffmpeg…) ne se compile pas
simplement pour Android. Mais tu as **deux vrais moyens** d'avoir l'app sur ton téléphone —
dont un qui produit un **vrai fichier .apk** à installer.

---

## Étape commune : héberger l'app (gratuit, ~10 min)

Il faut que l'app tourne quelque part en **HTTPS**. Le plus simple : **Render** (gratuit).

Prérequis : un compte **GitHub** et un compte **Render** (gratuits).

1. Mets ce dossier sur un dépôt GitHub (privé si tu veux).
2. Sur https://render.com → **New → Blueprint** → choisis ton dépôt.
   Render lit `render.yaml` et configure tout seul (build + démarrage).
   *(Sinon : New → Web Service → Build `pip install -r requirements-cloud.txt`,
   Start laissé vide, plan **Free**.)*
3. Déploie. Tu obtiens une URL du type `https://ai-choir-parts.onrender.com`.

Notes :
- Le **mode arrangement** (générer les pupitres depuis ta voix) marche sur le tier gratuit.
- Le **mode extraction** (séparer une chanson) est trop lourd pour le gratuit → garde-le en local.
- Sur le gratuit, l'app « s'endort » après inactivité : le 1er accès prend ~30 s.

---

## Moyen A — Installer comme PWA (sans APK, recommandé)

Sur ton Samsung, ouvre l'URL Render dans **Chrome** ou **Samsung Internet** :

- **Samsung Internet** : menu ☰ → **Ajouter la page à** → **Écran d'accueil**.
  Samsung crée une vraie entrée d'app (icône, plein écran).
- **Chrome** : menu ⋮ → **Installer l'application** / **Ajouter à l'écran d'accueil**.

Comme c'est en HTTPS, tu obtiens l'app **plein écran** avec son icône, comme une appli classique.

---

## Moyen B — Générer un vrai fichier .apk (PWABuilder)

Si tu veux réellement un `.apk` à installer/partager :

1. Va sur **https://www.pwabuilder.com** (outil gratuit de Microsoft).
2. Colle l'URL de ton app Render → **Start**.
3. Onglet **Android** → **Generate Package** → télécharge le `.zip`.
4. Dedans se trouve un **`.apk`** (signé, non signé selon l'option).
5. Envoie l'`.apk` sur ton Samsung, ouvre-le, autorise « installer des applis inconnues »,
   installe.

PWABuilder fabrique l'APK à partir de ta PWA (le manifest et l'icône sont déjà prêts dans le
projet). L'app ainsi installée pointe vers ton hébergement Render.

---

## iPhone (iOS)

Sur iPhone, il n'existe pas d'`.apk` ni d'app hors-ligne, mais l'installation PWA marche très bien :

1. Ouvre l'URL `https://…` dans **Safari** (pas Chrome sur iOS).
2. Bouton **Partager** (carré avec flèche) → **Sur l'écran d'accueil**.
3. Une icône **AI Choir Parts** apparaît et s'ouvre en plein écran, comme une app.

Tu peux **chanter directement** : le bouton 🎤 « Enregistrer ma voix » utilise le micro,
tu t'écoutes, puis tu génères les pupitres. (Autorise le micro quand Safari le demande.)

---

## Enregistrer ou importer

Dans l'app (iPhone ou Android), tu as le choix :
- **🎤 Enregistrer ma voix** : enregistre directement dans l'app, réécoute, puis génère.
- **Importer un fichier** : choisis un audio déjà enregistré sur le téléphone.

Enregistre **a cappella, au calme** pour un bon résultat (surtout la basse).

---

## Et un APK 100 % hors-ligne ?

Un APK qui embarque tout le calcul sur le téléphone (sans serveur) = réécriture native
(Kotlin + une lib de transposition sur l'appareil type SoundTouch/Rubber Band). C'est un projet
séparé, bien plus lourd. À cadrer seulement si le besoin hors-ligne est réel.
