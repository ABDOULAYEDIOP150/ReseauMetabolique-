from pathlib import Path

import pandas as pd
from rdflib import Dataset, Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

DOSSIER = Path("data/processed")

# 1) Les espaces de noms : des "préfixes" pour écrire des URI courtes
EX = Namespace("http://exemple.org/metabo/")          # notre vocabulaire (classes et propriétés)
DATA = Namespace("http://exemple.org/metabo/data/")   # nos données (un métabolite, une réaction...)
CHEBI = Namespace("http://purl.obolibrary.org/obo/CHEBI_")
KEGG = Namespace("https://identifiers.org/kegg.compound:")
MNX = Namespace("https://identifiers.org/metanetx.chemical:")


def uri_metabolite(reseau, ident):
    return DATA[f"{reseau}/metabolite/{ident}"]


def uri_reaction(reseau, ident):
    return DATA[f"{reseau}/reaction/{ident}"]


def ajouter(graphe, sujet, predicat, valeur, type_xsd=None):
    """Ajoute un triplet seulement si la valeur existe (pas de case vide dans le graphe)."""
    if pd.notna(valeur) and valeur != "":
        graphe.add((sujet, predicat, Literal(valeur, datatype=type_xsd)))


def main():
    metabolites = pd.read_csv(DOSSIER / "metabolites.csv")
    reactions = pd.read_csv(DOSSIER / "reactions.csv")
    participants = pd.read_csv(DOSSIER / "participants.csv")

    ds = Dataset()
    for prefixe, ns in [("ex", EX), ("data", DATA), ("chebi", CHEBI), ("kegg", KEGG), ("mnx", MNX)]:
        ds.bind(prefixe, ns)

    # 2) Le vocabulaire (l'"ontologie" minimale), dans un graphe à part
    onto = ds.graph(EX["ontologie"])
    onto.add((EX.Metabolite, RDF.type, RDFS.Class))
    onto.add((EX.Reaction, RDF.type, RDFS.Class))
    onto.add((EX.Participation, RDF.type, RDFS.Class))
    onto.add((EX.Metabolite, RDFS.label, Literal("Métabolite", lang="fr")))
    onto.add((EX.Reaction, RDFS.label, Literal("Réaction", lang="fr")))

    # 3) Un graphe nommé par réseau
    for reseau in sorted(metabolites.reseau.unique()):
        g = ds.graph(DATA[f"graphe/{reseau}"])

        # 3a) Les métabolites
        for m in metabolites[metabolites.reseau == reseau].itertuples():
            s = uri_metabolite(reseau, m.id)
            g.add((s, RDF.type, EX.Metabolite))
            ajouter(g, s, RDFS.label, m.nom)
            ajouter(g, s, EX.formule, m.formule)
            ajouter(g, s, EX.compartiment, m.compartiment)
            # Les liens vers les bases universelles : ce sont des URI, pas du texte
            if pd.notna(m.chebi):
                g.add((s, EX.chebi, CHEBI[str(m.chebi).replace("CHEBI:", "")]))
            if pd.notna(m.kegg):
                g.add((s, EX.kegg, KEGG[str(m.kegg)]))
            if pd.notna(m.metanetx):
                g.add((s, EX.metanetx, MNX[str(m.metanetx)]))

        # 3b) Les réactions
        for r in reactions[reactions.reseau == reseau].itertuples():
            s = uri_reaction(reseau, r.id)
            g.add((s, RDF.type, EX.Reaction))
            ajouter(g, s, RDFS.label, r.nom)
            ajouter(g, s, EX.equation, r.equation)
            g.add((s, EX.reversible, Literal(bool(r.reversible), datatype=XSD.boolean)))
            ajouter(g, s, EX.genes, r.genes)

        # 3c) Les participants : un lien direct + un nœud "participation" pour la stœchiométrie
        for p in participants[participants.reseau == reseau].itertuples():
            reaction = uri_reaction(reseau, p.reaction)
            metabolite = uri_metabolite(reseau, p.metabolite)
            lien = EX.aPourReactif if p.role == "reactif" else EX.aPourProduit
            g.add((reaction, lien, metabolite))

            participation = DATA[f"{reseau}/participation/{p.reaction}/{p.metabolite}"]
            g.add((participation, RDF.type, EX.Participation))
            g.add((participation, EX.reaction, reaction))
            g.add((participation, EX.metabolite, metabolite))
            g.add((participation, EX.role, Literal(p.role)))
            g.add((participation, EX.stoechiometrie, Literal(p.stoechiometrie, datatype=XSD.double)))

        print(f"{reseau:12} : {len(g):7} triplets")

    total = sum(len(g) for g in ds.graphs())
    print(f"{'TOTAL':12} : {total:7} triplets")

    # 4) Sauvegardes
    ds.serialize(DOSSIER / "graphe.trig", format="trig")      # tous les graphes nommés
    ds.serialize(DOSSIER / "graphe.nq", format="nquads")      # une ligne = un quadruplet
    print("Fichiers écrits : graphe.trig et graphe.nq")

    # 5) Montrer un petit morceau du graphe en Turtle
    g = ds.graph(DATA["graphe/e_coli_core"])
    extrait = Graph()
    extrait.namespace_manager = ds.namespace_manager
    for sujet in [uri_reaction("e_coli_core", "PFK"),
                  uri_metabolite("e_coli_core", "atp_c"),
                  DATA["e_coli_core/participation/PFK/atp_c"]]:
        for triplet in g.triples((sujet, None, None)):
            extrait.add(triplet)
    print("\n=== Extrait en Turtle : PFK, l'ATP et sa participation ===")
    print(extrait.serialize(format="turtle"))

    # 6) Le "pont" entre organismes : une même URI universelle utilisée par plusieurs réseaux
    print("=== Les ponts entre les 4 réseaux ===")
    for propriete in [EX.chebi, EX.kegg]:
        reseaux_par_uri = {}
        for g in ds.graphs():
            for _, _, uri in g.triples((None, propriete, None)):
                reseaux_par_uri.setdefault(uri, set()).add(g.identifier.split("/")[-1])
        communs = [u for u, r in reseaux_par_uri.items() if len(r) == 4]
        print(f"{propriete.split('/')[-1]:6} : {len(reseaux_par_uri):5} URI différentes, "
              f"{len(communs):3} présentes dans les 4 réseaux")

    print("\nL'ATP dans chaque réseau :")
    for g in ds.graphs():
        for s, _, uri in g.triples((None, EX.kegg, KEGG["C00002"])):
            chebi = g.value(s, EX.chebi)
            print(f"   {g.identifier.split('/')[-1]:12} {s.split('/')[-1]:8} kegg=C00002  chebi={chebi.split('_')[-1] if chebi else None}")
            break

if __name__ == "__main__":
    main()