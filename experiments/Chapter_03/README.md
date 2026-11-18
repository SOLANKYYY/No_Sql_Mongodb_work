# Experiment 03 · Document modelling, validation and GridFS

Model course schedules and enrolments, trace prerequisites, and compare ways to store comments and images with posts.

## Findings and evidence

Five posts illustrate embedded and referenced comments. The image exercise recorded one file over the 16 MiB document limit. Storing the five originals in GridFS used 101 chunks and kept the combined post documents at 5,233 bytes.

- [Course validation rules](Activity_3.1/activity_3_1_schema_validator.json)
- [BSON and image sizes](Activity_3.2_Try_It_Yourself/activity_3_2_try_it_yourself_sizes.json)
- [Chapter report](Chapter03_Activities_Report.docx)

## Activities

- [3.1 Validating embedded course data](Activity_3.1/README.md)
- [3.1 extension · Course prerequisites](Activity_3.1_Try_It_Yourself/README.md)
- [3.2 Embedded and referenced comments](Activity_3.2/README.md)
- [3.2 extension · Storing large images](Activity_3.2_Try_It_Yourself/README.md)

[All 18 experiments](../README.md)
