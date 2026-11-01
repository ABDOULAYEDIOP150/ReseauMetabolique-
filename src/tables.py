from pathlib import Path

import cobra
import pandas as pd

DOSSIER_BRUT = Path("data/raw")
DOSSIER_SORTIE = Path("data/processed")


def premier(valeur):
    """Une annotation peut être un texte ou une liste : on garde la première valeur."""
    if isinstance(valeur, list):
        return valeur[0] if valeur else None
    return valeur


def modele_vers_tables(modele, reseau):
    """Transforme UN modèle cobra en 3 tableaux pandas."""

    # 1) Tableau des métabolites : une ligne par métabolite
    metabolites = pd.DataFrame([
        {
            "reseau": reseau,
            "id": m.id,
            "nom": m.name,
            "formule": m.formula,
            "compartiment": m.compartment,
            "kegg": premier(m.annotation.get("kegg.compound")),
            "chebi": premier(m.annotation.get("chebi")),
            "metanetx": premier(m.annotation.get("metanetx.chemical")),
        }
        for m in modele.metabolites
    ])

    # 2) Tableau des réactions : une ligne par réaction
    reactions = pd.DataFrame([
        {
            "reseau": reseau,
            "id": r.id,
            "nom": r.name,
            "equation": r.reaction,
            "reversible": r.reversibility,
            "genes": r.gene_reaction_rule,
        }
        for r in modele.reactions
    ])

    # 3) Tableau des participants : une ligne par couple (réaction, métabolite)
    participants = pd.DataFrame([
        {
            "reseau": reseau,
            "reaction": r.id,
            "metabolite": m.id,
            "role": "reactif" if coef < 0 else "produit",
            "stoechiometrie": abs(coef),
        }
        for r in modele.reactions
        for m, coef in r.metabolites.items()
    ])

    return metabolites, reactions, participants


def main():
    toutes_met, toutes_rea, toutes_par = [], [], []

    for fichier in sorted(DOSSIER_BRUT.glob("*.xml*")):
        reseau = fichier.name.split(".")[0]          # "e_coli_core.xml.gz" -> "e_coli_core"
        print(f"Lecture de {reseau} ...")
        modele = cobra.io.read_sbml_model(str(fichier))
        met, rea, par = modele_vers_tables(modele, reseau)
        toutes_met.append(met)
        toutes_rea.append(rea)
        toutes_par.append(par)

    # On empile les tableaux des 4 réseaux
    metabolites = pd.concat(toutes_met, ignore_index=True)
    reactions = pd.concat(toutes_rea, ignore_index=True)
    participants = pd.concat(toutes_par, ignore_index=True)

    # Sauvegarde en CSV
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    metabolites.to_csv(DOSSIER_SORTIE / "metabolites.csv", index=False)
    reactions.to_csv(DOSSIER_SORTIE / "reactions.csv", index=False)
    participants.to_csv(DOSSIER_SORTIE / "participants.csv", index=False)

    # Ce qu'on a obtenu
    print("\n=== Taille des tableaux ===")
    print("metabolites :", metabolites.shape)
    print("reactions   :", reactions.shape)
    print("participants:", participants.shape)

    print("\n=== Lignes par réseau ===")
    print(pd.DataFrame({
        "metabolites": metabolites.groupby("reseau").size(),
        "reactions": reactions.groupby("reseau").size(),
        "participants": participants.groupby("reseau").size(),
    }))

    print("\n=== La réaction PFK dans le tableau des participants ===")
    pfk = participants[(participants.reseau == "e_coli_core") & (participants.reaction == "PFK")]
    print(pfk.to_string(index=False))

    print("\n=== Couverture des identifiants universels (% de métabolites) ===")
    print((metabolites.groupby("reseau")[["kegg", "chebi", "metanetx"]]
           .agg(lambda c: c.notna().mean() * 100).round(1)))


if __name__ == "__main__":
    main()