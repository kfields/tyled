<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" tiledversion="1.10.2" name="tiny-town" tilewidth="16" tileheight="16" spacing="1" tilecount="132" columns="12">
 <properties>
  <property name="piece:house_wood_grey" value="48,49,50;60,63,62;72,85,75"/>
  <property name="anchor:house_wood_grey" value="1,2"/>
  <property name="piece:house_wood_grey_wide" value="48,51,49,50;60,61,63,62;72,84,85,75"/>
  <property name="anchor:house_wood_grey_wide" value="2,2"/>
  <property name="piece:house_stone_red" value="52,53,54;64,67,66;76,89,79"/>
  <property name="anchor:house_stone_red" value="1,2"/>
  <property name="piece:house_stone_red_wide" value="52,55,53,54;64,65,67,66;76,88,89,79"/>
  <property name="anchor:house_stone_red_wide" value="2,2"/>
  <property name="piece:forest_green" value="6,7,8;18,19,20;30,31,32"/>
  <property name="anchor:forest_green" value="1,1"/>
  <property name="piece:forest_autumn" value="9,10,11;21,22,23;33,34,35"/>
  <property name="anchor:forest_autumn" value="1,1"/>
  <property name="piece:castle_courtyard" value="96,97,98;108,109,110;120,121,122"/>
  <property name="anchor:castle_courtyard" value="1,1"/>
  <property name="kind:castle_courtyard" value="nine_slice"/>
  <property name="piece:dirt_patch" value="12,13,14;24,25,26;36,37,38"/>
  <property name="anchor:dirt_patch" value="1,1"/>
  <property name="kind:dirt_patch" value="nine_slice"/>
  <property name="piece:castle_gate_house" value="99,100;111,112;123,124"/>
  <property name="anchor:castle_gate_house" value="1,2"/>
  <property name="piece:castle_gateway" value="123,124"/>
  <property name="anchor:castle_gateway" value="0,0"/>
  <property name="piece:well_roofed" value="92;104"/>
  <property name="anchor:well_roofed" value="0,1"/>
  <property name="piece:pine_tall" value="4;16"/>
  <property name="anchor:pine_tall" value="0,1"/>
  <property name="piece:pine_autumn_tall" value="3;15"/>
  <property name="anchor:pine_autumn_tall" value="0,1"/>
 </properties>
 <image source="kenney/tiny-town/Tilemap/tilemap.png" width="203" height="186"/>
 <tile id="0">
  <properties>
   <property name="name" value="grass"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="1">
  <properties>
   <property name="name" value="grass_tufts"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="2">
  <properties>
   <property name="name" value="grass_flowers"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="3">
  <properties>
   <property name="name" value="pine_autumn_top"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="4">
  <properties>
   <property name="name" value="pine_top"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="5">
  <properties>
   <property name="name" value="bush"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="bush"/>
  </properties>
 </tile>
 <tile id="6">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="7">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="8">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="9">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="10">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="11">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="12">
  <properties>
   <property name="name" value="dirt_nw"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="13">
  <properties>
   <property name="name" value="dirt_n"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="14">
  <properties>
   <property name="name" value="dirt_ne"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="15">
  <properties>
   <property name="name" value="pine_autumn_bottom"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="16">
  <properties>
   <property name="name" value="pine_bottom"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="17">
  <properties>
   <property name="name" value="sprout"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="18">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="19">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="20">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="21">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="22">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="23">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="24">
  <properties>
   <property name="name" value="dirt_w"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="25">
  <properties>
   <property name="name" value="dirt"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="26">
  <properties>
   <property name="name" value="dirt_e"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="27">
  <properties>
   <property name="name" value="pine_autumn"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="28">
  <properties>
   <property name="name" value="pine"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="29">
  <properties>
   <property name="name" value="mushrooms"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="30">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="31">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="32">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="33">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="34">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="35">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="tree"/>
  </properties>
 </tile>
 <tile id="36">
  <properties>
   <property name="name" value="dirt_sw"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="37">
  <properties>
   <property name="name" value="dirt_s"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="38">
  <properties>
   <property name="name" value="dirt_se"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="39">
  <properties>
   <property name="name" value="road_dirt_edge_w"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="40">
  <properties>
   <property name="name" value="road_dirt_edge_e"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="41">
  <properties>
   <property name="name" value="road_dirt"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="42">
  <properties>
   <property name="name" value="road_dirt_worn"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="43">
  <properties>
   <property name="name" value="road_cobble"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="44">
  <properties>
   <property name="name" value="fence_nw"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="45">
  <properties>
   <property name="name" value="fence_t"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="46">
  <properties>
   <property name="name" value="fence_ne"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="47">
  <properties>
   <property name="name" value="fence_post_n"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="48">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="49">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="50">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="51">
  <properties>
   <property name="name" value="chimney_grey"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="52">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="53">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="54">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="55">
  <properties>
   <property name="name" value="chimney_red"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="56">
  <properties>
   <property name="name" value="fence_w"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="57">
  <properties>
   <property name="name" value="cart"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="cart"/>
  </properties>
 </tile>
 <tile id="58">
  <properties>
   <property name="name" value="fence_e"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="59">
  <properties>
   <property name="name" value="fence_v"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="60">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="61">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="62">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="63">
  <properties>
   <property name="name" value="gable_grey"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="64">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="65">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="66">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="67">
  <properties>
   <property name="name" value="gable_red"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="68">
  <properties>
   <property name="name" value="fence_sw"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="69">
  <properties>
   <property name="name" value="fence_gap"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="70">
  <properties>
   <property name="name" value="fence_se"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="71">
  <properties>
   <property name="name" value="fence_post_s"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="72">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="73">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="74">
  <properties>
   <property name="name" value="doorway_wood"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="75">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="76">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="77">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="78">
  <properties>
   <property name="name" value="doorway_stone"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="79">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="80">
  <properties>
   <property name="name" value="fence_post_w"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="81">
  <properties>
   <property name="name" value="fence_h"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="82">
  <properties>
   <property name="name" value="fence_post_e"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="fence"/>
  </properties>
 </tile>
 <tile id="83">
  <properties>
   <property name="name" value="sign"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="sign"/>
  </properties>
 </tile>
 <tile id="84">
  <properties>
   <property name="name" value="window_wood"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="85">
  <properties>
   <property name="name" value="door_wood"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="86">
  <properties>
   <property name="name" value="door_wood_arch"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="87">
  <properties>
   <property name="name" value="door_wood_right"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="88">
  <properties>
   <property name="name" value="window_stone"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="house"/>
  </properties>
 </tile>
 <tile id="89">
  <properties>
   <property name="name" value="door_stone"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="90">
  <properties>
   <property name="name" value="door_stone_arch"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="91">
  <properties>
   <property name="name" value="door_stone_right"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="door"/>
  </properties>
 </tile>
 <tile id="92">
  <properties>
   <property name="name" value="well_roof"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="well"/>
  </properties>
 </tile>
 <tile id="93">
  <properties>
   <property name="name" value="coin"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="94">
  <properties>
   <property name="name" value="beehive"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="beehive"/>
  </properties>
 </tile>
 <tile id="95">
  <properties>
   <property name="name" value="target"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="target"/>
  </properties>
 </tile>
 <tile id="96">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="97">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="98">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="99">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="100">
  <properties>
   <property name="name" value="castle_parapet"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="101">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="102">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="103">
  <properties>
   <property name="name" value="castle_ladder"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="104">
  <properties>
   <property name="name" value="well"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="well"/>
  </properties>
 </tile>
 <tile id="105">
  <properties>
   <property name="name" value="bomb"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="106">
  <properties>
   <property name="name" value="log"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="107">
  <properties>
   <property name="name" value="bag"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="108">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="109">
  <properties>
   <property name="name" value="castle_floor"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="110">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="111">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="112">
  <properties>
   <property name="name" value="castle_portcullis"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="113">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="114">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="115">
  <properties>
   <property name="name" value="pickaxe"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="116">
  <properties>
   <property name="name" value="pitchfork"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="117">
  <properties>
   <property name="name" value="key"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="118">
  <properties>
   <property name="name" value="bow"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="119">
  <properties>
   <property name="name" value="arrow"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="120">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="121">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="122">
  <properties>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="123">
  <properties>
   <property name="name" value="castle_gate_left"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="124">
  <properties>
   <property name="name" value="castle_gate_right"/>
   <property name="walkable" type="bool" value="true"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="125">
  <properties>
   <property name="name" value="castle_wall_slit"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="126">
  <properties>
   <property name="name" value="castle_wall"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="castle"/>
  </properties>
 </tile>
 <tile id="127">
  <properties>
   <property name="name" value="axe"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="128">
  <properties>
   <property name="name" value="hammer"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="129">
  <properties>
   <property name="name" value="scythe"/>
   <property name="walkable" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="130">
  <properties>
   <property name="name" value="barrel"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="barrel"/>
  </properties>
 </tile>
 <tile id="131">
  <properties>
   <property name="name" value="barrel_water"/>
   <property name="walkable" type="bool" value="false"/>
   <property name="kind" value="barrel"/>
  </properties>
 </tile>
</tileset>
