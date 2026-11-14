# GymPro DZ — Logiciel de gestion de salle de sport

Gestion complète d'une salle de sport algérienne : adhérents, abonnements (durée ou séances), pointage par carte QR,
paiements en DA (Espèces, CCP/BaridiMob, Edahabia, CIB…), dettes, reçus, boutique & stock, dépenses, rapports.
Interface **Français / العربية / English**, responsive (PC, tablette, téléphone), mode sombre.
Base de données : **Supabase** (PostgreSQL dans le cloud). **Pas besoin de Docker.**

---

## 1. Fonctionnalités

| Module | Ce que ça fait |
|---|---|
| **Tableau de bord** | Adhérents actifs, expirations proches (bouton WhatsApp de rappel), visites du jour, dettes, recettes/dépenses/bénéfice du mois, graphiques |
| **Adhérents** | Fiche complète (photo webcam, groupe sanguin, notes médicales, contact d'urgence, CNI, assurance), recherche, filtres (actif / expire bientôt / expiré / en pause / dette / sexe / activité), archive, export Excel |
| **Abonnements** | Par durée (1 mois, 3 mois, 1 an…) ou par séances (carte 12 séances), remise, paiement partiel, renouvellement qui démarre à la fin de l'abonnement en cours, **pause** (Ramadan, voyage, blessure) avec jours rendus, ajout/retrait de jours |
| **Pointage** | Scanner USB, caméra du téléphone ou recherche par nom ; contrôle automatique (expiré, en pause, dette, séances), son + écran vert/rouge, alerte médicale, entrée forcée possible |
| **Carte adhérent** | Carte format bancaire imprimable avec QR code |
| **Paiements & reçus** | N° de reçu automatique, ticket 80 mm ou A5 (RC/NIF/NIS de la salle), frais d'inscription, assurance annuelle, export |
| **Dettes** | Liste de tous les adhérents qui doivent de l'argent + rappel WhatsApp |
| **Boutique** | Caisse (protéine, eau, créatine…), code-barres, vente à crédit pour un adhérent, stock & alertes, marge |
| **Dépenses** | Loyer, Sonelgaz, salaires, matériel… par catégorie |
| **Rapports** | Recettes / dépenses / bénéfice par période, par type, par mode de paiement, par offre, par employé, heures de pointe, jours les plus chargés |
| **Personnel** | Comptes avec rôles : Propriétaire, Gérant, Réceptionniste, Coach |
| **Paramètres** | Nom, logo, coordonnées, règles d'entrée, frais, message WhatsApp, sauvegarde JSON |
| **Licence** | Essai gratuit 14 jours puis clé de licence par installation (pour vendre le logiciel) |

---

## 2. Créer la base Supabase (5 minutes, une fois par salle)

1. Créez un compte gratuit sur **https://supabase.com** → **New project**.
   - Nom : par ex. `salle-atlas-oran`
   - **Database password** : choisissez-en un et **notez-le**
   - Région : **Europe (Frankfurt / eu-central-1)**, la plus proche de l'Algérie
2. Une fois le projet créé, cliquez sur **Connect** (en haut) → onglet **Connection string** → choisissez
   **Session pooler** (important : fonctionne avec toutes les connexions Internet, IPv4).
3. Copiez l'URL, qui ressemble à :
   ```
   postgresql://postgres.abcdefghij:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
   ```
   Remplacez `[YOUR-PASSWORD]` par votre mot de passe.
   ⚠ Si le mot de passe contient `@ # / : ?`, encodez-les (`@` → `%40`, `#` → `%23`, `/` → `%2F`).

Les tables sont créées automatiquement par l'installateur. Supabase garde aussi des sauvegardes automatiques.

---

## 3. Installation sur le PC de la salle (Windows 10/11)

1. Copiez le dossier `gympro` sur le PC (par ex. `C:\GymPro`), **pas dans Téléchargements**.
2. Double-cliquez sur **`INSTALLER.bat`**. Il va :
   - installer Python automatiquement s'il manque (sinon : python.org → Python 3.12, cochez *Add to PATH*) ;
   - installer les composants ;
   - vous demander **l'URL Supabase** (collez-la avec clic droit) ;
   - demander si les tablettes ou téléphones du Wi-Fi doivent avoir accès ;
   - créer les tables, les offres par défaut et le **compte propriétaire** (nom + mot de passe) ;
   - créer l'icône **« GymPro DZ » sur le Bureau** et dans le menu Démarrer ;
   - proposer le démarrage automatique avec Windows.
3. **Double-cliquez sur l'icône GymPro DZ** : le serveur démarre en arrière-plan (pas de fenêtre noire) et
   l'application s'ouvre dans sa propre fenêtre, comme un logiciel classique (Edge ou Chrome en mode application).

| Fichier | Rôle |
|---|---|
| `INSTALLER.bat` | Installation complète (une seule fois) |
| `DEMARRER.bat` | Même chose que l'icône du Bureau |
| `ARRETER.bat` | Arrête le serveur |
| `METTRE_A_JOUR.bat` | Après avoir copié une nouvelle version des fichiers |
| `.env` | Configuration (URL Supabase, port, accès Wi-Fi) |

**Utilisation sur tablette ou téléphone (même Wi-Fi)** : choisissez « o » à la question Wi-Fi (ou mettez `HOST=0.0.0.0`
dans `.env`), puis ouvrez `http://IP-DU-PC:8000` (l'installateur affiche l'adresse). Sur Android ou iPhone, faites
« Ajouter à l'écran d'accueil » pour avoir une icône.

**Matériel conseillé** : un lecteur QR/code-barres USB (~3 000 à 6 000 DA) pour le pointage, et une imprimante
thermique 80 mm pour les reçus.

### Linux / macOS
```bash
cp .env.example .env      # puis mettez votre DATABASE_URL
./start.sh
```

---

## 4. Premier démarrage (dans l'application)

1. **Paramètres** : nom, logo, adresse, téléphone, RC/NIF/NIS, frais d'inscription, assurance, horaires femmes,
   message WhatsApp.
2. **Offres & tarifs** : modifiez les offres d'exemple (prix en DA) ou créez les vôtres.
3. **Personnel** : créez un compte par réceptionniste ou coach.
4. **Adhérents → Nouvel adhérent** : la fiche et le premier abonnement se saisissent sur la même page.
5. Imprimez la **carte** de l'adhérent (QR code) ; à l'entrée, scannez-la sur la page **Pointage**.

---

## 5. Votre serveur de licences (essai 14 jours, activation, blocage à distance)

À faire **une seule fois**, avant de distribuer l'application :

1. Créez **votre propre** projet Supabase (par ex. `gympro-licences`). Ce n'est pas la base d'une salle :
   c'est votre base de vendeur.
2. Ouvrez **SQL Editor** → collez le contenu de `tools/license_server.sql` → **Run**.
3. Récupérez l'URL du projet et la clé **anon public** dans **Project Settings → API**.
4. Ouvrez `gym/license.py` et remplissez :
   ```python
   LICENSE_SECRET     = b"un-long-texte-secret-a-vous"
   LICENSE_SERVER_URL = "https://xxxx.supabase.co"
   LICENSE_SERVER_KEY = "eyJhbGciOi..."      # clé anon public
   VENDOR_PHONE       = "0550 12 34 56"      # affiché sur l'écran de blocage
   VENDOR_WHATSAPP    = "213550123456"       # bouton WhatsApp sur l'écran de blocage
   ```

**Ensuite, tout se fait automatiquement :**

| Moment | Ce qui se passe |
|---|---|
| La salle ouvre l'app la 1ʳᵉ fois | Elle s'enregistre seule dans votre table `licenses` → **essai 14 jours** |
| 5 derniers jours | Bandeau jaune « votre essai se termine dans X jours » |
| Jour 15 | L'app est **bloquée** : écran avec votre téléphone + WhatsApp. Les données restent intactes, et le propriétaire peut toujours télécharger une copie |
| La salle paie | Dans Supabase → **Table Editor → licenses** : `status = active`, `expires_at = 2027-11-14` → la salle clique « Vérifier à nouveau » et l'app est débloquée |
| Pas payé / problème | `status = suspended` (+ un `message` facultatif) → bloquée au prochain contrôle (toutes les 6 h ou au clic) |
| PC jamais connecté pendant 10 jours | Bloqué jusqu'à ce qu'il se reconnecte (empêche de couper Internet pour contourner) |

Des requêtes prêtes à l'emploi (prolonger de 7 jours, liste des essais qui finissent bientôt…) se trouvent en bas
de `tools/license_server.sql`.

**Clés hors ligne (option)** : pour une salle sans Internet fiable, `python tools/make_license.py <ID> 2027-12-31 "Salle"`
génère une clé à coller dans Paramètres → Licence. Une clé valide passe avant le statut en ligne.

> Ne donnez jamais aux salles le dossier `tools/` ni votre `LICENSE_SECRET`. En mode **lien** (section 6), la salle
> n'a pas accès au code : c'est le mode le plus sûr. En mode **installation sur PC**, le code Python est lisible :
> la protection suffit contre le partage, pas contre un développeur décidé.

---

## 6. Comment livrer l'application aux salles : 2 modes

| | **A. Lien (hébergé) — recommandé** | **B. Installation sur le PC de la salle** |
|---|---|---|
| Ce que la salle reçoit | Un lien `https://atlas.votre-domaine.com` + identifiants | Le dossier zip → `INSTALLER.bat` |
| Icône sur le Bureau | Oui : bouton **« Installer l'application »** dans Chrome/Edge (aussi sur téléphone) | Oui : créée par l'installateur |
| Marche sur téléphone/tablette hors Wi-Fi | Oui, partout | Seulement sur le Wi-Fi de la salle |
| Mises à jour | Vous, une seule fois pour toutes les salles (`update_all.sh`) | Copier les fichiers chez chaque salle |
| Contrôle des licences | Total (la salle n'a pas le code) | Bon |
| Coût pour vous | Un serveur VPS (~5–8 €/mois pour 20+ salles) + un nom de domaine (~1 500 DA/an) | Rien |
| Votre déplacement | Aucun | Installation sur place (ou à distance avec AnyDesk) |

Dans les deux modes, Internet est nécessaire (les données sont sur Supabase).

### Mode A — Mettre une salle en ligne (serveur Linux, sans Docker)
1. Louez un VPS Ubuntu 24.04 (Hetzner, Contabo, OVH…) et achetez un domaine (ex. `gympro-dz.com`).
2. Chez votre registrar DNS, créez un enregistrement **A** `*` (wildcard) → IP du VPS.
3. Copiez le zip sur le serveur, décompressez-le, puis (en root) :
   ```bash
   bash deploy/server/install_server.sh          # une seule fois
   bash /opt/gympro/app/deploy/server/add_gym.sh atlas atlas.gympro-dz.com vous@email.com
   ```
   Le script demande l'URL Supabase **de la salle**, crée les tables et le compte propriétaire, démarre le service
   et installe le certificat HTTPS gratuit.
4. Envoyez au gérant : le lien + son identifiant. Il ouvre le lien dans Chrome/Edge → **Installer l'application**.
5. Nouvelle version pour toutes les salles : `bash deploy/server/update_all.sh` depuis le nouveau dossier.

### Mode B — Installation sur le PC
Voir la section 3 (`INSTALLER.bat`). Pensez à remplir `gym/license.py` **avant** de copier le dossier.

---

## 7. Développement

```bash
pip install -r requirements.txt polib
python manage.py migrate
python manage.py seed_demo           # données de démo : admin / admin123
python manage.py runserver
```
- Sans `DATABASE_URL`, une base SQLite locale est utilisée (démo hors-ligne).
- Traductions : modifiez `tools/translations.py` puis lancez `python tools/build_translations.py`.
- Structure : `gym/models.py` (données + règles), `gym/views/` (pages), `gym/templates/gym/` (HTML),
  `gym/static/gym/` (CSS/JS), `accounts/` (utilisateurs & rôles).
