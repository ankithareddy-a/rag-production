{{ config(materialized='view') }}

select
    id as order_id,
    customer_id,
    total_amount as amount,
    created_at
from raw_orders
