# Raster Results Processing QGIS Plugin
Plugin to process hydraulic model results rasters - set (currently only one) of tools to make it easier to create
* Impact Rasters

Tools are primarily designed to work with TUFLOW outputs

## Impact Raster Creator
Tool that takes a Changed scenario and matches it to a Baseline scenario raster for the same event and calculates a grid of change in water level and/or change in extents

Tool takes advantage of tasks in QGIS 3 to enable multi-thread background processing to speed up creation of impact rasters for multiple events and/or scenarios

* On launching the tool identifies all loaded max water level rasters (h_Max), and attempts to identify a baseline file

* User can select which file to use an example baseline instead

* User then provides all event identifiers used in the file naming convention (\~eN~)

* All other baseline results will be identified from this

* Output location can be specified; By default the location is two levels above the baseline water level grid, in a folder called Impact
  * /Results
    * /Raw
      * /Model_Base_XXXX_v001
        * /grids
          * Model_Base_XXXX_v001_h_Max.asc
    * /**Impact**

* Naming convention follows:
  * PREFIX_[CHANGED]-[BASELINE]_EVENT_OP
    * PREFIX is the common element from both files
    * CHANGED is the details from changed after the prefix (excluding _h_Max)
    * BASELINE is the details from BASELINE after the prefix (excluding _h_Max)
    * EVENT is the events
    * OP is the output generated
  * Example
    * Baseline
      * Model_Base_XXXX_v001_h_Max
    * Changed
      * Model_Changed_XXXX_v001_h_Max
    * Output
      * Model_[Changed_XXXX_v001]-[Base_XXXX_v001]_XXXX_dh

* Outputs available are:
  * _dh
    * Change in water level between Changed and Baseline (no output in locations where either has no flooding)
    * Positive values indicate higher water level in the Changed scenario
  * _dx
    * Change in extents between Changed and Baseline (no output in locations where both have flooding or no flooding)
    * +99 indicates flooding only in the changed scenario; -99 indicates flooding only in the baseline scenario
  * _dh_dx
    * Combination of the above two outputs

* Outputs are in GeoTIFF format, in the projects projection

* The user can then select which outputs they wish to create; by default all outputs not currently in the workspace are selected for creation
