
  create or replace   view DE_SPEEDRUN.ANALYTICS.my_second_dbt_model
  
  
  
  
  as (
    -- Use the `ref` function to select from other models

select *
from DE_SPEEDRUN.ANALYTICS.my_first_dbt_model
where id = 1
  );

