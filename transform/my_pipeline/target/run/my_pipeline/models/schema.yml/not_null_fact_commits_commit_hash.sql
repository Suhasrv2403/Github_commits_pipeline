select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select commit_hash
from DE_SPEEDRUN.PUBLIC.fact_commits
where commit_hash is null



      
    ) dbt_internal_test