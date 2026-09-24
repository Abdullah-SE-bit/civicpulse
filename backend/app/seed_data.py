"""Hand-labelled sample complaints (Urdu-influenced English). (text, location, category, priority)."""

SEED_COMPLAINTS: list[tuple[str, str, str, str]] = [
    # water
    ("Burst water main flooding Street 12 since fajr, water entering ground floors", "Street 12, Block C", "water", "high"),
    ("Paani nahi aa raha since three days in our lane, tanker also not coming", "Gulshan Block 4", "water", "normal"),
    ("Sewage mixed drinking water from the tap, kids are getting stomach infection", "Model Colony, Lane 7", "water", "high"),
    ("Water pressure is very low every morning, hardly a bucket fills in one hour", "Sector F-10/2", "water", "low"),
    ("Pipe leaking near the mosque gate, water running on the road all day", "Jamia Masjid Road", "water", "normal"),
    ("Main valve broken outside the school, road turning into a pond after each supply time", "Government Girls School Road", "water", "high"),
    # electricity
    ("Transformer sparking near the park and smoke coming out, please send team urgently", "Shadman Park Chowk", "electricity", "high"),
    ("Load shedding for 8 hours daily in our mohalla even after the schedule said 2 hours", "Nishtar Colony", "electricity", "normal"),
    ("Live wire hanging low over the lane after last night's storm, children play here", "Street 5, Iqbal Town", "electricity", "high"),
    ("Meter reading is wrong and the bill is double, nobody at the office listens", "House 44, Block B", "electricity", "low"),
    ("Voltage keeps fluctuating and our fridge motor burnt twice this month", "Sector G-9", "electricity", "normal"),
    ("Electric pole is leaning dangerously after a truck hit it near the bus stop", "Ferozepur Road Bus Stop", "electricity", "high"),
    # sanitation
    ("Garbage not picked for two weeks, heap is now on the road and smell is unbearable", "Sabzi Mandi Chowk", "sanitation", "normal"),
    ("Sewer line overflowing in front of the clinic, dirty water entering the shops", "Main Market, Sector 11", "sanitation", "high"),
    ("Open gutter without cover next to the primary school, a child nearly fell in", "Street 9, Faisal Town", "sanitation", "high"),
    ("Kachra container is always full and dogs scatter it every night", "Block A, Johar Town", "sanitation", "low"),
    ("Drain choked after rain and mosquitoes are breeding, dengue cases in the street", "Lane 3, Wapda Town", "sanitation", "normal"),
    ("Sweeper has not come to our street for a month, please arrange cleaning", "Street 21, Bahria Enclave", "sanitation", "low"),
    # roads
    ("Big pothole on the main road, two motorcycles slipped this week", "Canal Road near Underpass", "roads", "normal"),
    ("Road caved in after the rain, a deep hole opened in the middle of the lane", "Street 14, Garden Town", "roads", "high"),
    ("Speed breaker is too high and damages cars, needs to be made proper", "Airport Road", "roads", "low"),
    ("Footpath broken and blocked by construction material, elderly people cannot walk", "Liberty Market", "roads", "low"),
    ("Traffic signal not working at the crossing and there is total chaos at school time", "Kalma Chowk", "roads", "high"),
    # streetlights
    ("Streetlight not working in our street for a month, snatching incidents happening at night", "Street 8, Model Town", "streetlights", "high"),
    ("Street lights are on in the daytime and wasting electricity, please fix the timer", "Ring Road, Sector 3", "streetlights", "low"),
    ("Lamp post fallen on the footpath after the storm and wires are exposed", "Mall Road", "streetlights", "high"),
    ("Whole lane is dark since the lights were removed for road work, nobody replaced them", "Lane 6, Township", "streetlights", "normal"),
    ("Two lights are flickering continuously outside the park, very irritating for residents", "Jinnah Park Gate 2", "streetlights", "low"),
    # other
    ("Stray dogs pack attacking people near the graveyard in the evening", "Karbala Road", "other", "normal"),
    ("Illegal encroachment by vendors is blocking the entrance of the dispensary", "Basic Health Unit, Sector 7", "other", "low"),
    ("Loudspeaker noise at midnight from the marriage hall every weekend", "Hall Road", "other", "low"),
    ("Old dangerous building is collapsing and cracks are increasing, people still living below", "Old City, Bazaar Lane", "other", "high"),
]
