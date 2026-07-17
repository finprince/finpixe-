from django.db import connection

def run():
    cursor = connection.cursor()
    try:
        cursor.execute("ALTER TABLE advance_allocation ADD COLUMN gst_registered VARCHAR(3) DEFAULT '';")
    except Exception as e:
        print(e)
    try:
        cursor.execute("ALTER TABLE pending_transaction ADD COLUMN gst_registered VARCHAR(3) DEFAULT '';")
    except Exception as e:
        print(e)
    try:
        cursor.execute("ALTER TABLE transaction_allocations ADD COLUMN gst_registered VARCHAR(3) DEFAULT '';")
    except Exception as e:
        print(e)
    print("Done")

if __name__ == "__main__":
    run()
