import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):
    valid_ids = [50885, 53089]

    reader = pd.read_csv(input_file, chunksize=chunksize)
    first_chunk = True

    total_rows_kept = 0
    for i, chunk in enumerate(reader):
        filtered_chunk = chunk[chunk[key_col].isin(valid_ids)]
        total_rows_kept += len(filtered_chunk)

        if first_chunk:
            filtered_chunk.to_csv(output_file, index=False, mode='w')
            first_chunk = False
        else:
            filtered_chunk.to_csv(output_file, index=False, mode='a', header=False)

        print(f"✔ 已处理第 {i+1} 块，保留 {len(filtered_chunk)} 行")

def remove_columns_from_csv(data_file, output_file):

    df = pd.read_csv(data_file)

    df = df[["subject_id", "charttime", "value"]]

    df.to_csv(output_file, index=False)
    print(f"输出文件保存至：{output_file}")

def drop_rows_with_empty_column(csv_file, column, output_file=None, remove_non_numeric=False):
    df = pd.read_csv(csv_file)
    initial_rows = len(df)
    
    # 删除缺失值
    df_clean = df.dropna(subset=[column])
    
    # 如果启用删除非数字行
    if remove_non_numeric:
        # 尝试将列转换为数值，无法转换的会变成NaN
        df_clean[column] = pd.to_numeric(df_clean[column], errors='coerce')
        # 删除新产生的NaN行（即原来的非数字行）
        df_clean = df_clean.dropna(subset=[column])
    
    cleaned_rows = len(df_clean)

    # 判断是否需要写入
    if cleaned_rows == initial_rows and (output_file is None or output_file == csv_file):
        print(f"未发现需要删除的行，无需写入文件。")
        return df_clean

    # 写入结果
    output_path = output_file if output_file else csv_file
    df_clean.to_csv(output_path, index=False)
    
    # 统计信息
    missing_removed = initial_rows - len(df.dropna(subset=[column]))
    non_numeric_removed = len(df.dropna(subset=[column])) - cleaned_rows if remove_non_numeric else 0
    
    if remove_non_numeric:
        print(f"已删除 {missing_removed} 行 {column} 为空的数据和 {non_numeric_removed} 行非数字数据，结果保存至 {output_path}")
    else:
        print(f"已删除 {missing_removed} 行 {column} 为空的数据，结果保存至 {output_path}")
    
    return df_clean

if __name__ == "__main__":

    #filter_large_csv_by_stay_ids('../../hosp/labevents.csv', './labbili.csv', 'itemid')
    #remove_columns_from_csv('./labbili.csv', './labbili.csv')
    drop_rows_with_empty_column('./labbili.csv', 'value', './labbili.csv', True)