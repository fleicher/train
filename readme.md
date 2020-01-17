Requirements: 
=============

### Fly 
- read flight data
    * took 
    * stored in `data.pickle`
    * numpy format: `['orig', 'dest', 'pas']`
    
- add `["lat", "long", "city", "ctry"]` 
    for `orig`/`dest` to each entry above
    
- store Mapping dict `mapping.json`:
    ```
    "Airport Code": {
        "name": "Airport Name",
        "rail": "1234567"
    } 
    ```
    
- draw a Europe map with
    * Airport Codes
    * Connecting Lines with thickness
    
### Rail
- get cities from 
    * `'High_Speed_Railroad_Map_of_Europe.svg'` 
    * xmldoc get certain `<text>` tags
    * apply fixes where names are wrong
    * store `[name, x, y, decoded]`

- rail =\> plane mapping
    * create 3 letter rail codes
    * foreach train city find matching airport(s), 
    and fix with `mapping_names.json`
    * store in `links_temp.json`: 
    ```
    "bei": {
        "city": "Berlin",
        "codes": [
            "EDDB",
            "EDDT"
        ],
        "links": {},
        "uic": null
    }
    ```
    
- get [rail times](https://www.eurail.com/content/dam/pdfs/eurail/resources/Eurail_2019-LR-def4.pdf)
    * store as `times.json`: 
        `["from", "to", time]`
    * get shortest train routes as:
    ```
    {
      "bel": {
          'bel': (0, ['bel']), 
          'dub': (130, ['bel', 'dub']), 
          'cok': (295, ['bel', 'dub', 'cok'])
        },
      "dub": {...}
    }
    ```

### Comparison
* find most used airports that don't have a train connection
* find most used airports that have the most routes going out for which are just too long
* categorize for east west europe, island etc by train station -> to filter and give better overview.

Draw Map 
* (use center of all airports) 
* filter out all direct connections that have faster/equal alternatives? 
* calc distance / speed for all connections. 