from pathlib import Path

import cobra

DOSSIER = Path("data/raw")

# 1) Vue d'ensemble : lire chaque réseau avec cobra
print("=== Vue d'ensemble ===")
for fichier in sorted(DOSSIER.glob("*.xml*")):
    modele = cobra.io.read_sbml_model(str(fichier))
    print(f"{fichier.name:20} id={modele.id:28} "
          f"métabolites={len(modele.metabolites):5} "
          f"réactions={len(modele.reactions):5} "
          f"gènes={len(modele.genes):5} "
          f"compartiments={len(modele.compartments):2}")

# 2) Zoom sur le petit réseau e_coli_core
modele = cobra.io.read_sbml_model(str(DOSSIER / "e_coli_core.xml.gz"))

print("\n=== Les compartiments ===")
for code, nom in modele.compartments.items():
    print(f"{code} -> {nom}")

print("\n=== Un métabolite : le glucose à l'extérieur de la cellule ===")
glucose = modele.metabolites.get_by_id("glc__D_e")
print("id          :", glucose.id)
print("nom         :", glucose.name)
print("formule     :", glucose.formula)
print("compartiment:", glucose.compartment)
print("annotations :")
for base, valeur in glucose.annotation.items():
    print(f"   {base:20} {valeur}")

print("\n=== Une réaction : la phosphofructokinase (PFK) ===")
pfk = modele.reactions.get_by_id("PFK")
print("id        :", pfk.id)
print("nom       :", pfk.name)
print("équation  :", pfk.reaction)
print("réactifs  :", [m.id for m in pfk.reactants])
print("produits  :", [m.id for m in pfk.products])
print("bornes    :", pfk.bounds)
print("réversible:", pfk.reversibility)
print("gènes     :", pfk.gene_reaction_rule)
modele
