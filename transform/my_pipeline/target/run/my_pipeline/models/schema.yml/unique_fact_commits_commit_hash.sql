select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

select
    commit_hash as unique_field,
    count(*) as n_records

from DE_SPEEDRUN.ANALYTICS.fact_commits
where commit_hash is not null
group by commit_hash
having count(*) > 1



      
    ) dbt_internal_test