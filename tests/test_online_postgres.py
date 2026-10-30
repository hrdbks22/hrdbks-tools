import os
import unittest
import uuid

import psycopg


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not configured")
class OnlinePostgresSchemaTests(unittest.TestCase):
    def test_hrd_tables_support_basic_crud_and_constraints(self):
        dsn = os.environ["TEST_DATABASE_URL"]
        nik = "TEST" + uuid.uuid4().hex[:12]
        username = "test_" + uuid.uuid4().hex[:8]
        with psycopg.connect(dsn) as conn:
            conn.execute(
                """INSERT INTO users(username,nama,role,shift,require_password,active)
                   VALUES (%s,%s,'Admin HRD','',1,1)""",
                (username, "Test User"),
            )
            conn.execute(
                """INSERT INTO employees(nik,nama,bagian,shift,masuk,keluar,status,sumber,updated_at)
                   VALUES (%s,'Test Employee','Produksi','E','2026-01-01','2026-12-31','S3','test','2026-01-01')""",
                (nik,),
            )
            conn.execute(
                """INSERT INTO attendance(nik,tanggal,jenis,hari,created_by)
                   VALUES (%s,'2026-01-02','Sakit',1,%s)""",
                (nik, username),
            )
            conn.execute(
                """INSERT INTO warnings(nik,jenis,tanggal,nomor,created_by)
                   VALUES (%s,'SP1','2026-01-03','TEST-SP1',%s)""",
                (nik, username),
            )
            self.assertEqual(conn.execute("SELECT count(*) FROM attendance WHERE nik=%s", (nik,)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT count(*) FROM warnings WHERE nik=%s", (nik,)).fetchone()[0], 1)
            with self.assertRaises(psycopg.errors.CheckViolation):
                conn.execute(
                    "INSERT INTO attendance(nik,tanggal,jenis,hari) VALUES (%s,'2026-01-04','INVALID',1)",
                    (nik,),
                )
            conn.rollback()
        with psycopg.connect(dsn) as conn:
            conn.execute("DELETE FROM attendance WHERE nik=%s", (nik,))
            conn.execute("DELETE FROM warnings WHERE nik=%s", (nik,))
            conn.execute("DELETE FROM employees WHERE nik=%s", (nik,))
            conn.execute("DELETE FROM users WHERE username=%s", (username,))


if __name__ == "__main__":
    unittest.main()
