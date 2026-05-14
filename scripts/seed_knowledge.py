"""
Seed the knowledge_chunks table with adoption process and care advice content.

Run locally:
    python scripts/seed_knowledge.py

    # Custom DB URL:
    DATABASE_URL=postgresql://pawmatch:pawmatch@localhost:5432/pawmatch python scripts/seed_knowledge.py

Idempotent: clears existing seeded rows and reinserts.
"""

import os
import uuid
import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)

CHUNKS = [
    # ─── La SPA ───────────────────────────────────────────────────────────────
    {
        "category": "adoption_process",
        "source": "la-spa",
        "title": "Comment adopter un animal à la SPA — vue d'ensemble",
        "content": (
            "La SPA (Société Protectrice des Animaux) est la plus grande association de protection animale en France. "
            "Elle gère des dizaines de refuges partout en France et propose des milliers d'animaux à l'adoption chaque année.\n\n"
            "Le processus d'adoption à la SPA se déroule en plusieurs étapes :\n"
            "1. Visite du refuge — vous rencontrez les animaux disponibles, accompagné d'un bénévole ou responsable adoption.\n"
            "2. Questionnaire d'adoption — un formulaire est rempli sur place pour évaluer votre mode de vie, votre logement, "
            "votre expérience avec les animaux et vos attentes.\n"
            "3. Entretien avec un responsable adoption — discussion approfondie sur la compatibilité entre l'animal choisi et votre situation.\n"
            "4. Signature du contrat d'adoption — engagement légal entre l'adoptant et la SPA.\n"
            "5. Paiement des frais d'adoption — variables selon l'espèce et l'âge de l'animal.\n"
            "6. L'animal repart avec vous — stérilisé, vacciné, identifié par puce électronique et vermifugé.\n\n"
            "Certains animaux peuvent nécessiter une visite à domicile préalable pour valider les conditions d'accueil "
            "(grands chiens, animaux à besoins spécifiques). La SPA se réserve le droit de refuser une adoption si les conditions ne sont pas réunies."
        ),
    },
    {
        "category": "adoption_process",
        "source": "la-spa",
        "title": "Documents requis pour adopter à la SPA",
        "content": (
            "Pour adopter un animal dans un refuge de la SPA, vous devez présenter les documents suivants :\n\n"
            "Documents obligatoires :\n"
            "- Pièce d'identité valide (carte nationale d'identité, passeport ou titre de séjour)\n"
            "- Justificatif de domicile de moins de 3 mois (facture EDF, eau, téléphone fixe ou quittance de loyer)\n\n"
            "Documents recommandés selon votre situation :\n"
            "- Si vous êtes locataire : autorisation écrite de votre propriétaire acceptant un animal de compagnie. "
            "Certains refuges le demandent systématiquement pour les chiens.\n"
            "- Photos de votre logement (jardin clôturé, espace disponible) — parfois demandées pour les grands gabarits.\n"
            "- Preuve d'un logement adapté pour les animaux avec besoins spécifiques.\n\n"
            "Aucune condition de revenus n'est exigée, mais la SPA évalue la capacité à assumer les frais vétérinaires courants. "
            "Toutes les pièces sont vérifiées sur place le jour de l'adoption."
        ),
    },
    {
        "category": "adoption_process",
        "source": "la-spa",
        "title": "Frais d'adoption à la SPA",
        "content": (
            "Les frais d'adoption à la SPA couvrent les soins apportés à l'animal pendant son séjour en refuge "
            "(vaccination, stérilisation, identification, vermifugation). Ils varient selon l'espèce et l'âge :\n\n"
            "Chiens :\n"
            "- Chiot (moins de 6 mois) : environ 250–350 €\n"
            "- Chien adulte (6 mois à 7 ans) : environ 150–250 €\n"
            "- Chien senior (plus de 7 ans) : environ 100–150 € (souvent réduit pour favoriser l'adoption)\n\n"
            "Chats :\n"
            "- Chaton (moins de 6 mois) : environ 150–200 €\n"
            "- Chat adulte : environ 100–150 €\n"
            "- Chat senior : environ 60–100 €\n\n"
            "Petits animaux (lapins, rongeurs, oiseaux) : environ 30–80 €\n\n"
            "Ces tarifs sont indicatifs et peuvent varier d'un refuge à l'autre. "
            "Certains refuges proposent des opérations 'adoption à prix réduit' sur des animaux difficiles à placer. "
            "Les frais d'adoption sont non remboursables sauf en cas de problème de santé grave non divulgué."
        ),
    },
    {
        "category": "adoption_process",
        "source": "la-spa",
        "title": "La visite à domicile et le suivi post-adoption à la SPA",
        "content": (
            "Pour certains animaux, la SPA peut organiser une visite à domicile avant de valider l'adoption. "
            "Cela concerne principalement :\n"
            "- Les chiens de grande taille ou à fort caractère\n"
            "- Les animaux ayant des antécédents de maltraitance\n"
            "- Les animaux nécessitant un environnement spécifique (jardin obligatoire, maison sans enfants en bas âge, etc.)\n\n"
            "La visite à domicile est réalisée par un bénévole de la SPA. Elle vise à vérifier que l'environnement correspond "
            "bien au profil de l'animal (espace, sécurisation du jardin, cohabitation avec d'autres animaux).\n\n"
            "Après l'adoption, certains refuges SPA assurent un suivi téléphonique dans les semaines qui suivent "
            "pour s'assurer de la bonne intégration de l'animal. "
            "En cas de difficultés, des conseils comportementalistes peuvent être proposés.\n\n"
            "Si l'adoption ne fonctionne pas, la SPA demande à ce que l'animal lui soit retourné plutôt qu'abandonné ou cédé à un tiers."
        ),
    },

    # ─── Seconde Chance ───────────────────────────────────────────────────────
    {
        "category": "adoption_process",
        "source": "secondechance",
        "title": "Comment adopter via Seconde Chance",
        "content": (
            "Seconde Chance est une plateforme d'annonces en ligne qui regroupe plus de 1 500 associations et refuges en France. "
            "Contrairement à la SPA, Seconde Chance n'est pas un refuge physique : elle sert d'intermédiaire entre les associations membres et les adoptants.\n\n"
            "Le processus d'adoption via Seconde Chance :\n"
            "1. Trouver un animal sur le site — vous pouvez filtrer par espèce, département et situation (adoption, placement familial).\n"
            "2. Contacter l'association directement — chaque annonce indique les coordonnées de l'association responsable de l'animal.\n"
            "3. Échange avec l'association — par email, téléphone ou formulaire de contact pour présenter votre situation et votre projet.\n"
            "4. Rencontre avec l'animal — organisée chez l'association ou la famille d'accueil.\n"
            "5. Validation du dossier — chaque association a ses propres critères (questionnaire, visite à domicile possible).\n"
            "6. Signature du contrat d'adoption et paiement des frais.\n\n"
            "Les délais et les exigences varient d'une association à l'autre. "
            "Certaines associations proposent une période d'essai avant l'adoption définitive."
        ),
    },
    {
        "category": "adoption_process",
        "source": "secondechance",
        "title": "Les associations partenaires de Seconde Chance — ce qu'il faut savoir",
        "content": (
            "Les associations présentes sur Seconde Chance sont des structures indépendantes (associations loi 1901) "
            "qui fonctionnent majoritairement grâce à des bénévoles et des familles d'accueil.\n\n"
            "Points importants à connaître :\n"
            "- Chaque association fixe ses propres critères d'adoption (logement, mode de vie, présence d'enfants, autres animaux).\n"
            "- Les délais de réponse varient — certaines associations bénévoles ne répondent que quelques jours par semaine.\n"
            "- Les animaux sont souvent en famille d'accueil plutôt qu'en cage, ce qui permet une meilleure évaluation du comportement.\n"
            "- Les frais d'adoption sont généralement entre 100 € et 300 € pour les chiens, 80 € à 200 € pour les chats.\n\n"
            "Conseils pour maximiser vos chances :\n"
            "- Rédigez un message de présentation soigné lors de votre premier contact.\n"
            "- Mentionnez votre logement, votre mode de vie, votre expérience avec les animaux et la composition de votre foyer.\n"
            "- Soyez patient : les associations sérieuses prennent le temps de bien évaluer les candidatures."
        ),
    },

    # ─── Général ──────────────────────────────────────────────────────────────
    {
        "category": "adoption_process",
        "source": "general",
        "title": "Se préparer à l'adoption — les questions à se poser",
        "content": (
            "Adopter un animal est un engagement à long terme. Avant de vous lancer, voici les questions essentielles :\n\n"
            "Mode de vie :\n"
            "- Avez-vous suffisamment de temps à consacrer à l'animal ? (Un chien nécessite minimum 2h de présence active par jour.)\n"
            "- Votre logement est-il adapté ? (Surface, présence d'un jardin, étage sans ascenseur pour certains chiens.)\n"
            "- Quid des vacances ? Avez-vous une solution de garde ?\n\n"
            "Budget mensuel estimé :\n"
            "- Nourriture : 30–50 €/mois pour un chat, 50–150 €/mois pour un chien selon la taille.\n"
            "- Vétérinaire courant (vaccins annuels, vermifuges, soins de base) : 200–400 €/an.\n"
            "- Assurance santé animale : 15–60 €/mois selon la formule.\n"
            "- Accessoires, jouets, toilettage : variable.\n\n"
            "Situation personnelle :\n"
            "- Si vous êtes locataire, votre bail autorise-t-il les animaux de compagnie ?\n"
            "- Les autres membres du foyer sont-ils tous d'accord ?\n"
            "- Y a-t-il des personnes allergiques ?\n\n"
            "Un animal adopté dans la précipitation est souvent un animal rendu. Prenez le temps de la réflexion."
        ),
    },
    {
        "category": "adoption_process",
        "source": "general",
        "title": "Les démarches administratives après l'adoption",
        "content": (
            "Une fois l'adoption finalisée, plusieurs démarches administratives sont à prévoir :\n\n"
            "Identification :\n"
            "- Tous les chiens et chats adoptés sont obligatoirement identifiés par puce électronique (ou tatouage).\n"
            "- Vous devez faire transférer l'identification à votre nom auprès de l'I-CAD (Fichier national d'identification des carnivores domestiques).\n"
            "- Cette démarche est généralement effectuée par le refuge ou le vétérinaire. Coût : environ 15–20 €.\n\n"
            "Passeport européen :\n"
            "- Si vous voyagez en Europe avec votre animal, un passeport européen est nécessaire (délivré par un vétérinaire).\n\n"
            "Assurance :\n"
            "- Non obligatoire, mais fortement recommandée pour les chiens (responsabilité civile incluse dans la plupart des assurances habitation).\n"
            "- Une assurance santé animale peut couvrir les frais vétérinaires imprévus.\n\n"
            "Déclaration en mairie :\n"
            "- Les chiens de 1re et 2e catégorie (dits 'dangereux') sont soumis à une déclaration obligatoire en mairie, "
            "ainsi qu'à des conditions de détention spécifiques (muselière, laisse, etc.).\n\n"
            "Carnet de santé :\n"
            "- Gardez précieusement le carnet de vaccination remis lors de l'adoption et faites-le mettre à jour annuellement."
        ),
    },

    # ─── Conseils soins — Chien ───────────────────────────────────────────────
    {
        "category": "care_advice",
        "source": "general",
        "title": "Prendre soin d'un chien — les bases",
        "content": (
            "Le chien est un animal social qui a besoin de présence, d'exercice et de stimulation pour être équilibré.\n\n"
            "Exercice :\n"
            "- Minimum 2 sorties par jour, d'au moins 30 minutes chacune.\n"
            "- Les races sportives (Border Collie, Husky, Malinois) nécessitent 2 à 3 heures d'activité quotidienne.\n"
            "- Les chiens seniors ou de petite taille peuvent se contenter de 2 x 20 minutes.\n\n"
            "Alimentation :\n"
            "- 1 à 2 repas par jour selon l'âge (les chiots mangent 3 à 4 fois par jour jusqu'à 6 mois).\n"
            "- Choisir des croquettes adaptées à la taille et l'âge (junior, adulte, senior, grande race).\n"
            "- Toujours laisser de l'eau fraîche disponible.\n\n"
            "Santé :\n"
            "- Vaccins annuels obligatoires : CHPPI (carré, hépatite, parvo, parainfluenza), rage si vous voyagez.\n"
            "- Antiparasitaires : vermifuge tous les 3 mois, traitement antipuce/tique mensuel ou saisonnier.\n"
            "- Détartrage vétérinaire recommandé tous les 1 à 2 ans.\n\n"
            "Les premiers jours chez vous :\n"
            "- Laissez l'animal explorer à son rythme, évitez les visites trop nombreuses les premiers jours.\n"
            "- Etablissez des règles claires dès le départ (accès aux meubles, chambre, etc.).\n"
            "- Un vétérinaire de référence doit être consulté dans les 15 jours suivant l'adoption."
        ),
    },
    {
        "category": "care_advice",
        "source": "general",
        "title": "Prendre soin d'un chat — les bases",
        "content": (
            "Le chat est un animal indépendant mais affectueux qui a besoin d'un environnement sécurisé et enrichi.\n\n"
            "Alimentation :\n"
            "- Eau fraîche disponible en permanence — les chats boivent peu, une fontaine peut les encourager.\n"
            "- Croquettes ou alimentation mixte (pâtées + croquettes) adaptées à l'âge.\n"
            "- Éviter de nourrir avec des restes humains (sel, oignons, chocolat sont toxiques).\n\n"
            "Litière :\n"
            "- Règle : une litière par chat + une supplémentaire.\n"
            "- Nettoyage quotidien, changement complet hebdomadaire.\n"
            "- Placer la litière loin de la gamelle.\n\n"
            "Enrichissement :\n"
            "- Griffoir obligatoire pour préserver vos meubles.\n"
            "- Espaces en hauteur (étagères, arbre à chat) pour que le chat se sente en sécurité.\n"
            "- Sessions de jeu quotidiennes avec une canne à plume ou jouets interactifs (15–20 min).\n\n"
            "Santé :\n"
            "- Vaccins : typhus (panleucopénie), coryza, leucose (surtout si sortie extérieure).\n"
            "- Antiparasitaires réguliers (antipuce, vermifuge).\n\n"
            "Les premiers jours :\n"
            "- Isolez le chat dans une pièce calme les premiers jours pour lui permettre de s'habituer aux odeurs et aux sons.\n"
            "- Ne forcez pas le contact — laissez-le venir à vous."
        ),
    },
    {
        "category": "care_advice",
        "source": "general",
        "title": "Prendre soin d'un lapin — les bases",
        "content": (
            "Le lapin est souvent sous-estimé : c'est un animal intelligent, social, qui peut vivre 8 à 12 ans.\n\n"
            "Logement :\n"
            "- En intérieur, le lapin a besoin d'au moins 4 m² de surface libre pour se déplacer.\n"
            "- Evitez les cages trop petites — le lapin doit pouvoir se dresser sur ses pattes arrière.\n"
            "- La litière doit être changée régulièrement (foin, litière végétale).\n\n"
            "Alimentation :\n"
            "- Foin en illimité — c'est la base (70% de la ration). Essentiel pour le transit et l'usure des dents.\n"
            "- Légumes frais quotidiens : persil, basilic, endive, feuilles de brocoli (pas de laitue iceberg).\n"
            "- Granulés en petite quantité (1 cuillère à soupe par kilo de poids/jour).\n"
            "- Eau fraîche disponible en permanence.\n\n"
            "Santé :\n"
            "- Vaccins obligatoires : Myxomatose et VHD2 (maladie hémorragique virale), renouvelés annuellement.\n"
            "- Stérilisation fortement recommandée : réduit les comportements territoriaux et les risques de cancer utérin chez la femelle.\n\n"
            "Comportement :\n"
            "- Le lapin est un animal grégaire. L'adopter en duo (après stérilisation) améliore significativement son bien-être.\n"
            "- Il ne faut pas le porter constamment — il préfère explorer au sol et interagir à son rythme."
        ),
    },

    # ─── Shelter info ─────────────────────────────────────────────────────────
    {
        "category": "shelter_info",
        "source": "la-spa",
        "title": "À propos de la SPA",
        "content": (
            "La SPA (Société Protectrice des Animaux), fondée en 1845, est la plus ancienne et la plus grande association "
            "de protection animale en France. Elle gère plus de 60 refuges et délégations sur l'ensemble du territoire.\n\n"
            "Chaque refuge SPA est autonome dans sa gestion quotidienne mais suit une charte nationale. "
            "Les conditions d'accueil, les horaires de visite et les frais d'adoption peuvent donc varier d'un refuge à l'autre.\n\n"
            "Pour trouver un refuge SPA près de chez vous ou obtenir des informations spécifiques sur un animal, "
            "rendez-vous directement sur le site de la SPA (la-spa.fr) ou contactez le refuge concerné par téléphone ou email. "
            "Chaque fiche animal sur PawMatch indique le refuge d'origine et un lien vers l'annonce originale."
        ),
    },
    {
        "category": "shelter_info",
        "source": "secondechance",
        "title": "À propos de Seconde Chance",
        "content": (
            "Seconde Chance est une plateforme française de mise en relation entre adoptants et associations de protection animale. "
            "Elle regroupe plus de 1 500 associations et refuges indépendants à travers toute la France.\n\n"
            "Contrairement à la SPA qui est une organisation centralisée, Seconde Chance est un annuaire et une vitrine. "
            "Les animaux listés sur Seconde Chance sont pris en charge par des associations autonomes — souvent de petites structures "
            "associatives bénévoles ou des familles d'accueil.\n\n"
            "Pour adopter un animal via Seconde Chance, vous devez contacter directement l'association mentionnée sur la fiche. "
            "Les délais, les critères et les frais dépendent entièrement de cette association. "
            "Chaque fiche animal sur PawMatch indique l'association responsable et un lien direct vers l'annonce originale sur Seconde Chance."
        ),
    },
]


def run():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    category VARCHAR NOT NULL,
                    source VARCHAR,
                    title VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(384),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()

            cur.execute("DELETE FROM knowledge_chunks")
            conn.commit()

            for chunk in CHUNKS:
                cur.execute(
                    """
                    INSERT INTO knowledge_chunks (id, category, source, title, content)
                    VALUES (gen_random_uuid(), %s, %s, %s, %s)
                    """,
                    (chunk["category"], chunk["source"], chunk["title"], chunk["content"]),
                )
            conn.commit()
            print(f"Seeded {len(CHUNKS)} knowledge chunks.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
