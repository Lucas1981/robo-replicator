# Robotticelli - the bot-based art replicator

So, this repository aims to let a Hugging Face SO-101 draw images based on actual image input. In order for this to work, we will have to:

- [ ] Have an interface with which we can upload a file
- [ ] Have an LLM connection that can take the contents of the file and generate an outline, "cartoon" like rendition of the original.
- [ ] Have functionality to turn this outline version into a vector-based image.
- [ ] Map the paths from the vector-based image to paths that the HF SO-101 should be able to operate on.
- [ ] Output commands for the HF SO-101 to run the generated output file.
