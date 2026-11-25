import pandas as pd

def calculate_sofa_liver(
    bilirubin_path,
    output_path,
    admissions_path=None,
    aggregation_window=1,
    method="worst",
):
    """Calculate liver SOFA scores from aggregated bilirubin values."""

    if (
        isinstance(aggregation_window, bool)
        or not isinstance(aggregation_window, int)
        or aggregation_window < 1
    ):
        raise ValueError("aggregation_window must be a positive integer.")

    if method not in {"worst", "mean"}:
        raise ValueError("method must be 'worst' or 'mean'.")

    if admissions_path is None:
        raise ValueError("admissions_path is required for all window sizes.")

    admissions = pd.read_csv(
        admissions_path,
        usecols=["subject_id", "admission_number", "admittime", "starttime", "endtime"],
        dtype={"subject_id": "string", "admission_number": "Int64"},
    )

    for column in ("admittime", "starttime", "endtime"):
        admissions[column] = (
            pd.to_datetime(admissions[column], errors="raise")
            .dt.floor("h")
            .astype("datetime64[ns]")
        )

    if admissions.isna().any().any():
        raise ValueError("Admission identifiers and timestamps must not be missing.")

    if admissions["endtime"].lt(admissions["starttime"]).any():
        raise ValueError("Admission endtime must not precede starttime.")

    admissions = admissions.drop_duplicates().reset_index(drop=True)
    if admissions.duplicated(["subject_id", "admission_number"]).any():
        raise ValueError("Each subject/admission_number must identify one admission interval.")

    df = pd.read_csv(
        bilirubin_path,
        usecols=["subject_id", "charttime", "value"],
        dtype={"subject_id": "string"},
    )

    # Exclude subjects absent from admissions for every window size.
    df = df.loc[df["subject_id"].isin(admissions["subject_id"])].copy()

    # Floor all observation timestamps to the hour.
    df["charttime"] = (
        pd.to_datetime(df["charttime"], errors="raise")
        .dt.floor("h")
        .astype("datetime64[ns]")
    )
    df["value"] = pd.to_numeric(df["value"], errors="raise")

    if df[["subject_id", "charttime"]].isna().any().any():
        raise ValueError("subject_id and charttime must not be missing.")

    # Missing bilirubin values do not contribute to window aggregation.
    df = df.dropna(subset=["value"]).copy()
    output_columns = ["subject_id", "admission_number", "charttime", "sofa_liver"]

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    # Match observations to admission intervals for every window size.
    # If hourly rounding creates a shared boundary, prefer the latest start.
    df = pd.merge_asof(
        df.sort_values("charttime", kind="stable"),
        admissions.sort_values("starttime", kind="stable"),
        by="subject_id",
        left_on="charttime",
        right_on="starttime",
        direction="backward",
        allow_exact_matches=True,
    )
    df = df.loc[df["charttime"].le(df["endtime"])].copy()

    if df.empty:
        return pd.DataFrame(columns=output_columns)

    if aggregation_window > 1:
        # Floor division also assigns observations before admission correctly.
        window = pd.Timedelta(hours=aggregation_window)
        window_number = (df["charttime"] - df["admittime"]) // window
        df["charttime"] = (
            df["admittime"]
            + pd.to_timedelta(
                window_number * aggregation_window,
                unit="h",
            )
        )

    # Aggregate within each matched admission without mixing separate stays.
    aggregation = "max" if method == "worst" else "mean"
    result = (
        df.groupby(
            ["subject_id", "admission_number", "charttime"],
            as_index=False,
        )["value"]
        .agg(aggregation)
    )

    # Apply inclusive bilirubin thresholds in mg/dL.
    result["sofa_liver"] = 0
    result.loc[result["value"].ge(1.2), "sofa_liver"] = 1
    result.loc[result["value"].ge(2), "sofa_liver"] = 2
    result.loc[result["value"].ge(6), "sofa_liver"] = 3
    result.loc[result["value"].ge(12), "sofa_liver"] = 4

    # Omit normal windows and do not create windows without observations.
    output = (
        result.loc[result["sofa_liver"].gt(0), output_columns]
        .sort_values(["subject_id", "admission_number", "charttime"])
        .reset_index(drop=True)
    )
    output.to_csv(output_path, index=False)

    return output

if __name__ == "__main__":
    calculate_sofa_liver('bilirubin.csv', 'sofa_liver_1_worst.csv',
                         '../repo_label_m4_public/admissions_merged.csv',
                         aggregation_window=1, method="worst")