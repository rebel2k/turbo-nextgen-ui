# Readme

## Run the program
```pipenv shell
streamlit run main.py
```

## Things to add

* [ADDITION] Switch dataframes view to something better?
* [ADDITION] List all placement policies and automation policies affecting a given VM
* [ADDITION] Sums of all resources reclaimable on different resize actions
* [ADDITION] Stats of the whole environment (number of workloads, etc.)

## Things to fix

* [FIX] get_stats() --> rewrite the function so it supports multiples metrics in one call

## Things done

* [FIX] get_stats() --> in case there's no capacity, function return an error
* [ADDITION] Add stats for VMs (number of vCPUs, ...)