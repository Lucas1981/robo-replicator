# Robo Replicator

This should provide functionality for the Hugging Face SO-101 to interpret a set of paths to draw, extracted from an actual image. For this to work we will need to:

- [ ] Have an interface to load an image.
- [ ] Have an integration with an AI service that can port this image for us to an image that is a "cartoon" outline version of the image with very few lines.
- [ ] Convert the image to a vector-based image that has the actual paths
- [ ] Map the paths to a set of paths that a HF SO-101 can interpret it terms of from/to movements to draw each of the pahts. This should assume:
  - [ ] The bot should navigate to the start of each path with the pen "off" the drawing surface
  - [ ] The bot should put the pen down on the surface
  - [ ] The bot should then trace the path to the end of the surface
  - [ ] The bot should lift the pen off the paper surface again
  - [ ] The pen should be able to handle bezier curves in addition to just straight paths.
  - [ ] The paths relative to start/end of the image should be scaled such that they correspont with coordinates of the drawing surface.
- [ ] Output the set of paths to a file format that would execute each of the required path movements.
