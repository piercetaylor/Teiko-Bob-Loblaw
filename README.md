This repo was created as a start to Teiko's Technical interview : Under Construction


Immune cell population data from Bob Loblaw at Loblaw Bio
    - File is cell-count.csv, has metadata
    - To understand how his drug candidate affects immune cell populations:
        - design python program to follow 4 analysis steps:
        1. Design SQL database
            - SQLite
            - load_data.py in root to
                - init data base
                - load all rows from cell-count.csv
        2. What is the frequency of each cell type in each sample?
            Display summary:
                sample: the sample id as in column sample in cell-count.csv

                total_count: total cell count of sample

                population: name of the immune cell population (e.g. b_cell, cd8_t_cell, etc.)

                count: cell count

                percentage: relative frequency in percentage
        3. responder vs non-responder analysis: 
                Compare the differences in cell population relative frequencies of melanoma patients receiving miraclib who respond (responders) versus those who do not (non-responders), with the overarching aim of predicting response to the treatment miraclib. Response information can be found in column "response", with value "yes" for responding and value "no" for non-responding. Please only include PBMC samples.

                Visualize the population relative frequencies comparing responders versus non-responders using a boxplot of for each immune cell population.

                Report which cell populations have a significant difference in relative frequencies between responders and non-responders. Statistics are needed to support any conclusion to convince Barry of Bob’s findings. 
        4. Identify all melanoma PBMC samples at baseline (time_from_treatment_start is 0) from patients who have been treated with miraclib. 

            Among these samples, extend the query to determine:

                How many samples from each project

                How many subjects were responders/non-responders 

                How many subjects were males/females
        5. Dashboard for visualization



