{{ config(materialized='table') }}

select
    customer_id,
    count(*) as order_count,
    sum(amount) as total_revenue
from {{ ref('stg_orders') }}
group by customer_id
