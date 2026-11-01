import sqlite3
import time

import pandas as pd

BASE = "data/processed/metabolisme.db"
connexion = sqlite3.connect(BASE)


def montrer(titre, sql, parametres=()):
    print(f"\n=== {titre} ===")
    print(pd.read_sql_query(sql, connexion, params=parametres).to_string(index=False))


# Q1 — Combien de métabolites et de réactions par réseau ?
montrer("Q1 : taille de chaque réseau", """
    SELECT m.reseau,
           COUNT(*) AS nb_metabolites,
           (SELECT COUNT(*) FROM reactions r WHERE r.reseau = m.reseau) AS nb_reactions
    FROM metabolites m
    GROUP BY m.reseau
""")

# Q2 — Les participants de PFK, avec le nom des molécules (jointure)
montrer("Q2 : la réaction PFK avec les noms", """
    SELECT p.role, p.stoechiometrie, m.id, m.nom
    FROM participants p
    JOIN metabolites m
      ON m.reseau = p.reseau AND m.id = p.metabolite
    WHERE p.reseau = ? AND p.reaction = ?
    ORDER BY p.role DESC
""", ("e_coli_core", "PFK"))

# Q3 — Les HUBS : métabolites reliés au plus grand nombre de réactions
montrer("Q3 : les 10 hubs d'e_coli_core (beaucoup de liens)", """
    SELECT p.metabolite, m.nom, COUNT(*) AS degre
    FROM participants p
    JOIN metabolites m ON m.reseau = p.reseau AND m.id = p.metabolite
    WHERE p.reseau = ?
    GROUP BY p.metabolite, m.nom
    ORDER BY degre DESC
    LIMIT 10
""", ("e_coli_core",))

# Q4 — Les métabolites avec UN SEUL lien (culs-de-sac du réseau)
montrer("Q4a : combien de métabolites n'ont qu'une seule réaction, par réseau", """
    SELECT reseau, COUNT(*) AS nb_metabolites_degre_1
    FROM (
        SELECT reseau, metabolite
        FROM participants
        GROUP BY reseau, metabolite
        HAVING COUNT(*) = 1
    )
    GROUP BY reseau
""")

montrer("Q4b : exemples dans iJO1366 (peu de liens)", """
    SELECT p.metabolite, m.nom, COUNT(*) AS degre
    FROM participants p
    JOIN metabolites m ON m.reseau = p.reseau AND m.id = p.metabolite
    WHERE p.reseau = ?
    GROUP BY p.metabolite, m.nom
    HAVING COUNT(*) = 1
    ORDER BY p.metabolite
    LIMIT 5
""", ("iJO1366",))

# Q5 — Les métabolites ISOLÉS : présents dans le réseau mais dans aucune réaction
montrer("Q5 : métabolites sans aucune réaction (LEFT JOIN ... IS NULL)", """
    SELECT m.reseau, COUNT(*) AS nb_isoles
    FROM metabolites m
    LEFT JOIN participants p
      ON p.reseau = m.reseau AND p.metabolite = m.id
    WHERE p.metabolite IS NULL
    GROUP BY m.reseau
""")

# Q6 — Les molécules communes aux 4 organismes (grâce à l'identifiant KEGG)
montrer("Q6 : nombre de molécules KEGG présentes dans les 4 réseaux", """
    SELECT COUNT(*) AS nb_molecules_communes
    FROM (
        SELECT kegg
        FROM metabolites
        WHERE kegg IS NOT NULL
        GROUP BY kegg
        HAVING COUNT(DISTINCT reseau) = 4
    )
""")

# ---------------------------------------------------------------
# OPTIMISATION : la même requête, sans puis avec index
# ---------------------------------------------------------------
REQUETE = "SELECT reseau, reaction FROM participants WHERE metabolite = ?"


def plan_et_temps(etiquette):
    plan = connexion.execute("EXPLAIN QUERY PLAN " + REQUETE, ("atp_c",)).fetchall()
    debut = time.perf_counter()
    for _ in range(500):                                   # 500 fois pour que le temps soit mesurable
        connexion.execute(REQUETE, ("atp_c",)).fetchall()
    duree = (time.perf_counter() - debut) * 1000
    print(f"\n--- {etiquette} ---")
    print("Plan  :", plan[0][-1])
    print(f"Temps : {duree:.0f} ms pour 500 requêtes")


print("\n=== Q7 : optimisation avec un index ===")
connexion.execute("DROP INDEX IF EXISTS idx_participants_metabolite")
plan_et_temps("SANS index")

connexion.execute("CREATE INDEX idx_participants_metabolite ON participants (metabolite)")
plan_et_temps("AVEC index")

connexion.close()