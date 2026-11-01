import sqlite3
from pathlib import Path

import pandas as pd

DOSSIER = Path("data/processed")
BASE = DOSSIER / "metabolisme.db"

SCHEMA = """
DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS reactions;
DROP TABLE IF EXISTS metabolites;

CREATE TABLE metabolites (
    reseau        TEXT NOT NULL,
    id            TEXT NOT NULL,
    nom           TEXT,
    formule       TEXT,
    compartiment  TEXT,
    kegg          TEXT,
    chebi         TEXT,
    metanetx      TEXT,
    PRIMARY KEY (reseau, id)
);

CREATE TABLE reactions (
    reseau      TEXT NOT NULL,
    id          TEXT NOT NULL,
    nom         TEXT,
    equation    TEXT,
    reversible  INTEGER,
    genes       TEXT,
    PRIMARY KEY (reseau, id)
);

CREATE TABLE participants (
    reseau          TEXT NOT NULL,
    reaction        TEXT NOT NULL,
    metabolite      TEXT NOT NULL,
    role            TEXT CHECK (role IN ('reactif', 'produit')),
    stoechiometrie  REAL CHECK (stoechiometrie > 0),
    PRIMARY KEY (reseau, reaction, metabolite),
    FOREIGN KEY (reseau, reaction)   REFERENCES reactions (reseau, id),
    FOREIGN KEY (reseau, metabolite) REFERENCES metabolites (reseau, id)
);
"""


def main():
    connexion = sqlite3.connect(BASE)
    connexion.execute("PRAGMA foreign_keys = ON")      # SQLite ne vérifie les clés étrangères que si on le demande
    connexion.executescript(SCHEMA)

    # L'ordre compte : d'abord les tables "parents", puis la table de liaison
    for table in ["metabolites", "reactions", "participants"]:
        df = pd.read_csv(DOSSIER / f"{table}.csv")
        df.to_sql(table, connexion, if_exists="append", index=False)
        print(f"{table:13} : {len(df):6} lignes chargées")

    connexion.commit()

    # Vérification : les clés étrangères sont-elles toutes respectées ?
    erreurs = connexion.execute("PRAGMA foreign_key_check").fetchall()
    print("Liens cassés :", len(erreurs))
    connexion.close()
    print("Base créée :", BASE)


if __name__ == "__main__":
    main()