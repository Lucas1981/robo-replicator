# Robotticelli

Functionality for the Hugging Face SO-101 to draw paths extracted from an image:

- [x] Interface to load an image (upload or webcam)
- [x] AI service for cartoon-style outline (`gpt-image-1` image edit)
- [x] Bitmap → vector SVG paths (OpenCV + scikit-image + skan)
- [x] SVG → SO-101 joint trajectories (pen up/down, bezier support, canvas scaling)
- [x] LeRobotDataset v3.0 zip export via `/api/robot-dataset` (includes `replay-virtual.sh` and `replay-follower.sh`)
