import pandas as pd
import os

def concat_csv_files(folder_path, output_file):
    # List to hold dataframes
    dfs = []
    if os.path.exists(output_file):
        os.remove(output_file)
    # Iterate over each file in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('california_output.csv') or filename.endswith('virginia_output.csv'):
            continue
        if filename.endswith('output.csv'):
            # Construct full file path
            file_path = os.path.join(folder_path, filename)
            # Read the CSV file and append to list
            df = pd.read_csv(file_path)
            dfs.append(df)

    # Concatenate all dataframes
    concatenated_df = pd.concat(dfs, ignore_index=True)
    if os.path.exists(output_file):
        os.remove(output_file)
    # Save the concatenated dataframe to a new CSV file
    concatenated_df.to_csv(output_file, index=False)

    print(f"Concatenated CSV saved as {output_file}")

# Example usage
folder_path = 'data'
output_file = 'data/all_output.csv'
concat_csv_files(folder_path, output_file)