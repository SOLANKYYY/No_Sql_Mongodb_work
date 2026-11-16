Exercise 6 - Indexing Strategies and Performance Tuning
=======================================================

HOW TO RUN (Windows PowerShell)
-------------------------------
1. Make sure your local MongoDB service is running:
     Get-Service -Name MongoDB          (Status should be Running)

2. Open PowerShell INSIDE this exercise-6 folder, e.g.:
     cd C:\Users\omnso\Downloads\exercise-6

3. Install dependencies (one time):
     pip install -r requirements.txt

4. Run the four scripts, one at a time:
     python activity-6.1\lab_6_1_index_design.py
     python activity-6.1-tryit\lab_6_1_tryit_index_stats.py
     python activity-6.2\lab_6_2_compare_index_strategies.py
     python activity-6.2-tryit\lab_6_2_tryit_covered_query.py

   Each script takes roughly 10-60 seconds (50,000 documents are generated in 6.1).

WHAT EACH SCRIPT SAVES AUTOMATICALLY (in its own activity folder)
------------------------------------------------------------------
  output.txt   - everything printed in the terminal (UTF-8)
  *.json       - the MongoDB data as JSON (this is the "MongoDB file (JSON)")

  activity-6.1/         output.txt, index_design_results.json, products.json
  activity-6.1-tryit/   output.txt, index_stats_results.json, products_tryit_sample.json
  activity-6.2/         output.txt, index_strategy_results.json, write_perf_test.json
  activity-6.2-tryit/   output.txt, covered_query_results.json, covered_query_demo.json

COMPASS SCREENSHOTS (connect to mongodb://localhost:27017)
-----------------------------------------------------------
  6.1        nosql_labs -> products -> "Indexes" tab
  6.1 tryit  nosql_labs -> index_stats_results -> Documents
  6.2        nosql_labs -> index_strategy_results -> Documents
  6.2 tryit  nosql_labs -> covered_query_results -> Documents

FINAL ZIP LAYOUT
----------------
  exercise-6/
    activity-6.1/          script + JSON + output.txt
    activity-6.1-tryit/    script + JSON + output.txt
    activity-6.2/          script + JSON + output.txt
    activity-6.2-tryit/    script + JSON + output.txt
    config/                shared helpers (needed to run the scripts)
    NoSQL_Exercise_6_Report.docx

NOTE: the scripts reset (drop and recreate) their own collections every run,
so they are safe to run again.
