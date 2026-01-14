select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select author_name
from DE_SPEEDRUN.PUBLIC.fact_commits
where author_name is null



      
    ) dbt_internal_test