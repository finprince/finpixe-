import pandas as pd

def process_data():
    df1 = pd.DataFrame({"A": [1, 2]})
    df2 = pd.DataFrame({"A": [3, 4]})
    
    # Legacy Pandas 1.x syntax (Deprecated in 1.4, removed in 2.0)
    # The Oracle will fail on Pandas 2.x with AttributeError
    df_final = df1.append(df2)
    
    print("Data processing complete.")
    print(df_final)

if __name__ == "__main__":
    process_data()
