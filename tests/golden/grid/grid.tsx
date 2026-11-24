<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" tiledversion="1.10.2" name="grid" tilewidth="8" tileheight="8" spacing="1" margin="2" tilecount="12" columns="4">
 <properties>
  <property name="piece:house" value="4,5,6;8,9,10"/>
  <property name="anchor:house" value="2,1"/>
  <property name="piece:roof" value="8,9;10,-"/>
  <property name="anchor:roof" value="0,1"/>
 </properties>
 <image source="grid.png" width="39" height="30"/>
 <tile id="0">
  <properties>
   <property name="name" value="grass"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="1">
  <properties>
   <property name="name" value="water"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="depth" type="int" value="2"/>
   <property name="speed" type="float" value="0.5"/>
  </properties>
 </tile>
 <tile id="2">
  <properties>
   <property name="walkable" type="bool" value="true"/>
   <property name="label" value="a &#34;quoted&#34; &lt;b&gt; &amp; more"/>
  </properties>
 </tile>
 <tile id="3">
  <properties>
   <property name="walkable" type="bool" value="true"/>
   <property name="label" value="a &#34;quoted&#34; &lt;b&gt; &amp; more"/>
  </properties>
 </tile>
 <tile id="4">
  <properties>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="5">
  <properties>
   <property name="name" value="stall"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="food_stall"/>
  </properties>
 </tile>
 <tile id="6">
  <properties>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="7">
  <properties>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="8">
  <properties>
   <property name="name" value="roof_left"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="9">
  <properties>
   <property name="name" value="roof_right"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="10">
  <properties>
   <property name="name" value="door"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="11">
  <properties>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
</tileset>
