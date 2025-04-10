# vibe2gml
a simple app for vibe coding with game maker studio 2. It will generate a txt file with all of your event code and yy file data. you can upload that txt file to llm's for vibe coding. Also allows you to paste event code directly into the app to avoid gms2 interface. Generating the txt file for the llm can make troubleshooting a lot easier, and it makes it a lot easier to work on something over multiple llm sessions. You can also paste code directly in the app, press save, and gms2 will update automatically if you have the option to monitor changes in the settings - it can be faster to paste multiple events this way. 
<img width="827" alt="v1" src="https://github.com/user-attachments/assets/6b0e7d18-411a-45af-b8d6-063b684f18e7" />

<img width="827" alt="2" src="https://github.com/user-attachments/assets/c59ba30a-eac4-4fe9-ad2b-967e1c9fe010" />

```[Export Example]
// GML and YY Data Export from Project: C:/Users/zacks/GameMakerProjects/k2
// Total GML Files Found: 11
======================================================================

// ----- Start GML: Object: Obj_grid / Create_0 -----
// ----- GML Path: objects\Obj_grid\Create_0.gml -----

/// @description Initialize Grid Settings

// --- Grid Properties ---
// Size of each grid cell in pixels (e.g., 64x64)
grid_size = 64;

// Calculate grid dimensions based on the room size
// 'div' performs integer division (ignores remainder)
grid_width = room_width div grid_size;  // Number of columns
grid_height = room_height div grid_size; // Number of rows

// --- Drawing ---
// Ensure this object's Draw event runs
visible = true;

// Set a depth that ensures it draws behind the player but potentially above the background
// Higher numbers are further back.
// Make sure your background layer in the Room Editor has a depth HIGHER than this (e.g., 1000)
depth = 100;

--------------------------------------------------[End GML]-----------

// ----- Associated YY File: Obj_grid -----
// ----- YY Path: objects\Obj_grid\Obj_grid.yy -----

{
  "$GMObject":"",
  "%Name":"Obj_grid",
  "eventList":[
    {"$GMEvent":"v1","%Name":"","collisionObjectId":null,"eventNum":0,"eventType":0,"isDnD":false,"name":"","resourceType":"GMEvent","resourceVersion":"2.0",},
    {"$GMEvent":"v1","%Name":"","collisionObjectId":null,"eventNum":0,"eventType":8,"isDnD":false,"name":"","resourceType":"GMEvent","resourceVersion":"2.0",},
  ],
  "managed":true,
  "name":"Obj_grid",
  "overriddenProperties":[],
  "parent":{
    "name":"Objects",
    "path":"folders/Objects.yy",
  },
  "parentObjectId":null,
  "persistent":false,
  "physicsAngularDamping":0.1,
  "physicsDensity":0.5,
  "physicsFriction":0.2,
  "physicsGroup":1,
  "physicsKinematic":false,
  "physicsLinearDamping":0.1,
  "physicsObject":false,
  "physicsRestitution":0.1,
  "physicsSensor":false,
  "physicsShape":1,
  "physicsShapePoints":[],
  "physicsStartAwake":true,
  "properties":[],
  "resourceType":"GMObject",
  "resourceVersion":"2.0",
  "solid":false,
  "spriteId":null,
  "spriteMaskId":null,
  "visible":true,
}

==============================[End YY]================================
This is an example of the output. The script combines all of this data for everything in
the project folder and outputs to a txt file for LLM. helpful in troubleshooting or vibe coding

