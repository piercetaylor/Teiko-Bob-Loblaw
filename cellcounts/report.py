"""Print the Part 2 and Part 3 results and write them to outputs/."""
from contextlib import closing

import pandas as pd

from cellcounts import frequencies, responders
from cellcounts.db import OUTPUT_DIR, connect_readonly, population_labels


def main() -> None:
    """Run the analysis against cell-count.db."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    with closing(connect_readonly()) as conn:
        table = frequencies.frequency_table(conn)
        comparison = responders.summarize(conn)
        cohort = responders.cohort_frequencies(conn)
        labels = population_labels(conn)

    print("Part 2: relative frequency of each population in each sample (first 20 rows)")
    print(table.head(20).to_string(index=False))
    print(f"\n{len(table)} rows written to {OUTPUT_DIR / 'frequencies.csv'}\n")
    table.to_csv(OUTPUT_DIR / "frequencies.csv", index=False)

    print("Part 3: responders vs non-responders, melanoma, miraclib, PBMC")
    print(comparison.to_string(index=False))
    comparison.to_csv(OUTPUT_DIR / "responders_comparison.csv", index=False)

    fig = responders.boxplot(
        responders.subject_means(cohort),
        labels,
        title="Melanoma PBMC on miraclib: responders vs non-responders (subject means)",
    )
    fig.write_html(OUTPUT_DIR / "responders_boxplot.html")


if __name__ == "__main__":
    main()
