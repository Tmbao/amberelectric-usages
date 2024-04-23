# [Unofficial] Amber Electric Usages

This is a data update coordinator for Amber Electric subscribers. Some subscribers (e.g. residents of NSW) are usually not able to get live data from smart meters and the data is often delay-ed by one day, and therefore the mechanism of a typical HA sensor doesn't work. This custom component takes a different approach to populate the data as statistics to HA, which can also be used in energy dashboard.

This is an addition and does not replace the mainstream Amber Electric sensor in HA core.

## Installation instructions
1. Make sure that you've had HACS installed (see [here](https://hacs.xyz/docs/user) for instructions).
2. Once HACS is installed, add the [](https://github.com/Tmbao/amberelectric-usages.git) as a custom repository (Integration type), then you should be able to find this integration (**Amber Electric - Usages**) via HACS Integration and download it.
3. Once you've downloaded the integration, make sure to restart your Home Assistant Server. 
4. Come to **Devices & Services** in your Settings, hit **Add Integration** and find Amber Electric Usages. You'll need the API key to use this integration, which can be obtained following [this other instruction](https://www.home-assistant.io/integrations/amberelectric/#getting-an-api-key).
5. Once the integration is successfully configured, you should be able to see the new statistics written to your HAS via the integration. _Note that the statistics are not linked to the integration and they can only be found in your **Developer Tools > Statistics**. However, you should be able to use them in your Energy dashboard._
