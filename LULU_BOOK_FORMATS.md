# Lulu Book Format Specifications for Children's Books

## Common Children's Book Sizes from Lulu

Based on Lulu's available formats, here are the most suitable sizes for children's books:

### Recommended Children's Book Formats

#### 1. **Square Small (8.5" x 8.5" | 216 x 216 mm)**
- **Best for**: Picture books, early readers
- **Aspect Ratio**: 1:1 (Square)
- **Image Dimensions**: 768x768 pixels (matches our current scene generation)
- **Cover Dimensions**: 768x768 pixels

#### 2. **Portrait Small (6" x 9" | 152 x 229 mm)**  
- **Best for**: Chapter books, early chapter books
- **Aspect Ratio**: 2:3
- **Image Dimensions**: 512x768 pixels
- **Cover Dimensions**: 512x768 pixels

#### 3. **Portrait Large (8.5" x 11" | 216 x 279 mm)**
- **Best for**: Activity books, educational books
- **Aspect Ratio**: 11:14 (approximately 3:4)
- **Image Dimensions**: 663x850 pixels
- **Cover Dimensions**: 663x850 pixels

#### 4. **Landscape (11" x 8.5" | 279 x 216 mm)**
- **Best for**: Storybooks, panoramic illustrations
- **Aspect Ratio**: 4:3
- **Image Dimensions**: 850x663 pixels
- **Cover Dimensions**: 850x663 pixels

#### 5. **Custom Square Large (10" x 10" | 254 x 254 mm)**
- **Best for**: Premium picture books, coffee table style
- **Aspect Ratio**: 1:1
- **Image Dimensions**: 768x768 pixels (can be upscaled)
- **Cover Dimensions**: 768x768 pixels

### Print Quality Calculations

For 300 DPI print quality:
- 6" x 9" = 1800 x 2700 pixels (we generate 512x768 then upscale)
- 8.5" x 8.5" = 2550 x 2550 pixels (we generate 768x768 then upscale)  
- 8.5" x 11" = 2550 x 3300 pixels (we generate 663x850 then upscale)

Our high-res fix with R-ESRGAN 4x+ upscaler handles the final quality enhancement.
