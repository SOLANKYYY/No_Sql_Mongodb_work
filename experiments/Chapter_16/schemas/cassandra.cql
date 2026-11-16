-- Exact query-oriented designs used by scripts/lab16.py.
CREATE KEYSPACE IF NOT EXISTS exercise16 WITH replication = {'class':'SimpleStrategy','replication_factor':1};
CREATE TABLE IF NOT EXISTS exercise16.student_courses (
  student_id text, course_id text, course_title text,
  PRIMARY KEY ((student_id), course_id)
);
CREATE TABLE IF NOT EXISTS exercise16.course_students (
  course_id text, student_id text, student_name text,
  PRIMARY KEY ((course_id), student_id)
);
CREATE TABLE IF NOT EXISTS exercise16.audit_by_student (
  student_id text, event_time timestamp, event_id uuid, action text, course_id text,
  PRIMARY KEY ((student_id), event_time, event_id)
) WITH CLUSTERING ORDER BY (event_time DESC, event_id ASC);
CREATE TABLE IF NOT EXISTS exercise16.user_profiles (
  user_id text, event_time timestamp, event_id text, txn_id text, amount double, merchant text,
  PRIMARY KEY ((user_id), event_time, event_id)
) WITH CLUSTERING ORDER BY (event_time DESC, event_id ASC);
-- Queries after RUN_16.ps1:
SELECT * FROM exercise16.student_courses WHERE student_id='S1';
SELECT * FROM exercise16.course_students WHERE course_id='C1';
SELECT * FROM exercise16.user_profiles WHERE user_id='U1' LIMIT 10;
-- Shared-course peers require looking up each S1 course in course_students,
-- unioning the student IDs and excluding S1. No ALLOW FILTERING is used.
