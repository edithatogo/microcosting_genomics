
import pandas as pd

# Create a dictionary with the mappings
mapping = {
    'Step': [
        'Registration', 'Name Check', 'Completion of forms', 'Unpacking/Triaging ',
        'Rapid Registration of the sample ', 'Data Entry / Data Review ', 'Venepuncture',
        'Referrer Liaison - MS', 'gDNA Extraction Kit - Labwork', 'gDNA QC - Labwork',
        'Bioinformatics pipeline maintenance and development', 'Case Setup', 'Case QC'
    ],
    'Label': [
        'AS', 'AS', 'AS', 'AS', 'AS', 'AS', 'LT', 'MS', 'LT', 'LT', 'BI', 'BI', 'BI'
    ]
}

# Create a dataframe from the dictionary
df_mapping = pd.DataFrame(mapping)

# Save the mapping to a CSV file
mapping_file_path = '/home/doughnut/github/unimelb-phd-phase-1/data/step_to_label_mapping.csv'
df_mapping.to_csv(mapping_file_path, index=False)

print(f"Mapping saved to {mapping_file_path}")
