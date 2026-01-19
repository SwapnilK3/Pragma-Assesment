from django.db import migrations

# it is custom migration for starting we don't have the sequence
# if we make docker up and direct test it will fail for this we need sequence
# below is for that taken help of llm to write

class Migration(migrations.Migration):
    """Create order number sequence for PostgreSQL."""

    dependencies = [
        ('orders', '0003_remove_orderitem_discounted_amount_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE SEQUENCE IF NOT EXISTS order_order_number_seq START 1;",
            reverse_sql="DROP SEQUENCE IF EXISTS order_order_number_seq;",
        ),
    ]
