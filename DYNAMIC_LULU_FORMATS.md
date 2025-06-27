# Dynamic Lulu Book Format Support

## 🎯 Overview

Your worker now supports **dynamic book dimensions** based on actual Lulu publishing specifications. Instead of fixed dimensions, the worker generates the **highest possible resolution** while maintaining the correct aspect ratio for the chosen book format, which can then be upscaled to 300 DPI during post-processing.

## 📚 Available Lulu Book Formats

### Standard Children's Book Formats

| Format ID | Name | Physical Size | Aspect Ratio | Generation Size | Best For |
|-----------|------|---------------|--------------|-----------------|----------|
| `pocket_book` | Pocket Book | 4.25" × 6.875" | 0.618 | 512×832 | Pocket-sized books |
| `us_trade` | US Trade | 6" × 9" | 0.667 | 576×864 | Standard chapter books |
| `royal` | Royal | 6.14" × 9.21" | 0.667 | 584×876 | Premium books |
| `crown_quarto` | Crown Quarto | 7.44" × 9.69" | 0.768 | 640×832 | Academic books |
| `us_letter` | US Letter | 8.5" × 11" | 0.773 | 680×880 | Activity books |
| `square_small` | Square Small | 8.5" × 8.5" | 1.0 | 768×768 | Picture books |
| `landscape` | Landscape | 11" × 8.5" | 1.294 | 880×680 | Panoramic storybooks |
| `square_large` | Square Large | 10" × 10" | 1.0 | 896×896 | Premium art books |

## 🔧 How It Works

### 1. User Selects Format During Funnel
```typescript
// From your Next.js book creation funnel
const bookSettings = {
  book_format: "us_trade",  // User choice from Lulu formats
  story_style: "picture_book",
  // ... other settings
};
```

### 2. Worker Generates Optimal Resolution
The worker automatically:
- ✅ Calculates the highest generation resolution for the format
- ✅ Maintains exact aspect ratio for the chosen Lulu format  
- ✅ Optimizes for later upscaling to 300 DPI
- ✅ Applies format-specific settings for quality

### 3. Post-Processing Upscaling
After generation, images are upscaled to final print dimensions:

| Format | Generation Size | → | 300 DPI Print Size |
|--------|----------------|---|-------------------|
| US Trade (6"×9") | 576×864 | → | 1800×2700 |
| Square Small (8.5"×8.5") | 768×768 | → | 2550×2550 |
| Square Large (10"×10") | 896×896 | → | 3000×3000 |

## 📝 API Usage Examples

### Story Scene Generation with Book Format
```json
{
  "input": {
    "scene_prompts": [
      "A brave little mouse in a magical forest",
      "The mouse meets a wise old owl"
    ],
    "book_format": "us_trade",
    "story_style": "picture_book",
    "reference_images": ["data:image/jpeg;base64,..."],
    "story_id": "my-story-123"
  }
}
```

### Book Cover with Specific Format
```json
{
  "input": {
    "generation_type": "book_cover",
    "title": "The Magic Adventure", 
    "book_format": "square_small",
    "story_style": "picture_book",
    "theme": "magical forest adventure"
  }
}
```

### Custom Dimensions (Advanced)
```json
{
  "input": {
    "scene_prompts": ["..."],
    "custom_width": 1024,
    "custom_height": 768,
    "story_style": "picture_book"
  }
}
```

## 🎨 Format-Specific Optimizations

Each format is optimized for its intended use:

### Picture Books (Square Formats)
- **square_small**: Perfect 1:1 ratio, great for children's picture books
- **square_large**: Premium quality for coffee table style books

### Chapter Books (Portrait Formats)  
- **us_trade**: Standard 6"×9" for novels and chapter books
- **royal**: Slightly larger premium format
- **pocket_book**: Compact size for travel books

### Activity Books (Letter Formats)
- **us_letter**: Wide format perfect for workbooks and activity books
- **crown_quarto**: Academic book standard

### Panoramic Books (Landscape)
- **landscape**: Wide format for panoramic illustrations

## 🔍 Response Format

The worker returns detailed format information:

```json
{
  "images": ["base64..."],
  "book_format_info": {
    "book_format": "us_trade",
    "generation_size": "576x864",
    "format_name": "US Trade (6\" x 9\")",
    "aspect_ratio": 0.667
  },
  "print_info": {
    "print_width": 1800,
    "print_height": 2700,
    "print_size_inches": [6, 9],
    "dpi": 300,
    "format_name": "US Trade (6\" x 9\")"
  }
}
```

## 🚀 Integration with Vertelmoment.nl

### 1. Book Format Selection in Funnel
Add format selection to your book creation flow:

```typescript
const BookFormatSelector = () => {
  const [selectedFormat, setSelectedFormat] = useState('square_small');
  
  return (
    <select value={selectedFormat} onChange={(e) => setSelectedFormat(e.target.value)}>
      <option value="square_small">Square Small (8.5" × 8.5") - Picture Books</option>
      <option value="us_trade">US Trade (6" × 9") - Chapter Books</option>
      <option value="square_large">Square Large (10" × 10") - Premium Books</option>
      {/* ... other formats */}
    </select>
  );
};
```

### 2. Pass Format to Image Generation
```typescript
const generateImages = async () => {
  const response = await fetch('/api/generate-image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scene_prompts: storyScenes,
      book_format: selectedFormat,  // From user selection
      story_style: selectedStyle,
      reference_images: characterImages
    })
  });
};
```

### 3. Store Format for Later Processing
Save the book format with the order for final print preparation:

```typescript
const orderData = {
  story_id: 'unique-id',
  book_format: 'us_trade',
  scenes: generatedScenes,
  cover: generatedCover,
  // ... other order details
};
```

## ✅ Benefits

- 🎯 **Exact Lulu Compliance**: Generates images that perfectly match Lulu's specifications
- 📐 **Optimal Resolution**: Highest quality possible for each format
- 🔄 **Scalable Workflow**: Easy to add new formats as Lulu expands options
- 💡 **Smart Defaults**: Sensible format selection based on book type
- 🖼️ **Preview Accuracy**: Generated covers match final print proportions
- ⚡ **Efficient Processing**: No wasted resolution on inappropriate dimensions

Your worker now provides **professional-grade print preparation** while maintaining the flexibility to work with any Lulu book format! 🎊
