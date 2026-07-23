<!--
ATTRIBUTION (added by cycleform, accessed 2026-07-23)
Source dataset: ModalShare — Prieto-Curiel, R. & Ospina, J. P.,
"Large cities are less efficient for sustainable transport: The ABC of mobility".
Complexity Science Hub / EAFIT.
Repo: https://github.com/rafaelprietocuriel/ModalShare  (file: ModalShare.csv)
Cite via the repo's CITATION.cff. The dataset is itself compiled from many
underlying sources (Eurostat, US/CA/AU census, EPOMM, EF China, ...), referenced
per row in the DataSource / DataLink columns.
Used in cycleform as the PRIMARY cycling-rate outcome (commute-to-work share);
see cycleform/ASSUMPTIONS.md > Outcomes. Original README follows verbatim.
-->

# ModalShare
Modal share across metropolitan areas.
The data contains the modal share distribution. The data has 1092 observations, corresponding to 876 metropolitan areas. 

## Variable description

CityID - unique identifier for the metropolitan area. Repeated IDs correspond to two or more observations for the same city.

ObsID - unique identifier of the observation. 

year - year of the sample

LastObservation - binary, detailing whether the number corresponds to the latest observation of the city

Country - name of the country

state_name - name of the state if available

state_abbr - state abbreviation if available

City - name of the city

metro_names - name of the metropolitan area if available (mostly in the US). The name for some cities corresponds to the largest municipality of the metropolitan area

population - estimated population corresponding to the year of the observations

longitude - x coordinate

latitude - y coordinate

Walking - % of people that walk to work

Cycling - % of people that cycle to work

Active - % of people that have active mobility to work, including walking, cycling and others

Bus - % of people that use public transport to work

Car - % of people that use car to work

IncomeGroup - Income group of the country, according to the World Bank classification

Region - world region  - Europe anc Central Asia; Latin America and Caribbean; East Asia and Pacific; South Asia; North America; Sub-Saharan Africa

DataSource - name of the data source reported

DataLink -  link to the data reported
