<h1>Story Generation Worker - A1111 with Batch Processing</h1>

[![RunPod](https://api.runpod.io/badge/runpod-workers/worker-a1111)](https://www.runpod.io/console/hub/runpod-workers/worker-a1111)

- Runs [Automatic1111 Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) with enhanced story generation capabilities
- Comes pre-packaged with the [**Deliberate v6**](https://huggingface.co/XpucT/Deliberate) model
- **NEW**: Batch story generation with character and style consistency
- **NEW**: Print-quality output optimized for storybook creation (768x768)
- **NEW**: Multiple artistic style LoRAs for different story aesthetics

---

## Features

### 🎨 Story Generation
- **Batch Processing**: Generate multiple story scenes in one request
- **Character Consistency**: Use reference images to maintain character appearance across scenes
- **Style Consistency**: Automatic seed locking ensures consistent artistic style throughout the story
- **Print Optimization**: 768x768 resolution optimized for upscaling to 300 DPI print quality
- **Book Cover Generation**: Specialized book cover creation with portrait format (512x768)

### 🎭 Available Story Styles (LoRAs)
- `picture_book` - Classic children's book illustration style
- `3d_animation` - 3D animated movie style
- `clay_animation` - Claymation/stop-motion style
- `watercolor` - Soft watercolor painting style
- `geometric` - Modern geometric illustration
- `paper_cutout` - Paper cutout art style
- `soft_anime` - Soft anime/manga style
- `block_world` - Minecraft-like block style

---

## API Usage

### Story Batch Generation (New!)

Generate a complete story with multiple scenes and consistent characters:

```json
{
  "input": {
    "scene_prompts": [
      "A young girl sitting by a window reading a book, peaceful afternoon",
      "The same girl walking through a magical forest with tall trees",
      "The girl meeting a friendly talking rabbit in a clearing"
    ],
    "reference_images": ["data:image/jpeg;base64,/9j/4AAQ..."],
    "story_style": "picture_book",
    "story_id": "my_story_123",
    "character_strength": 0.65,
    "lora_weight": 1.0,
    "steps": 35,
    "width": 768,
    "height": 768
  }
}
```

### Book Cover Generation (New!)

Generate a book cover with portrait format optimized for printing:

```json
{
  "input": {
    "generation_type": "book_cover",
    "title": "The Magic Forest Adventure",
    "subtitle": "A Tale of Friendship",
    "theme": "magical forest adventure with talking animals",
    "story_style": "picture_book",
    "reference_images": ["data:image/jpeg;base64,/9j/4AAQ..."]
  }
}
```

### Single Scene Generation (Backward Compatible)

The original API still works for single image generation:

```json
{
  "input": {
    "prompt": "a photograph of an astronaut riding a horse",
    "negative_prompt": "text, watermark, blurry, low quality", 
    "steps": 25,
    "cfg_scale": 7,
    "width": 768,
    "height": 768,
    "sampler_name": "DPM++ 2M Karras"
  }
}
```

### Service Information

Get available features and LoRAs:

```json
{
  "input": {
    "action": "get_info"
  }
}
```

---

## Parameters

### Story Generation Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `scene_prompts` | array | Array of scene descriptions for batch generation | - |
| `reference_images` | array | Base64 encoded reference images for character consistency | `[]` |
| `story_style` | string | LoRA name for artistic style | `"picture_book"` |
| `story_id` | string | Unique ID for reproducible results | auto-generated |
| `character_strength` | float | How strongly to apply reference image (0.0-1.0) | `0.65` |
| `lora_weight` | float | Strength of the style LoRA (0.0-2.0) | `1.0` |

### Standard Stable Diffusion Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `prompt` | string | Text description of the image | - |
| `negative_prompt` | string | What to avoid in the image | See defaults |
| `steps` | integer | Number of diffusion steps (15-50) | `35` |
| `cfg_scale` | float | How closely to follow the prompt (1-20) | `7.5` |
| `width` | integer | Image width in pixels | `768` |
| `height` | integer | Image height in pixels | `768` |
| `sampler_name` | string | Sampling method | `"DPM++ 2M Karras"` |

---

## Response Format

### Story Batch Response

```json
{
  "story_id": "my_story_123",
  "total_scenes": 3,
  "style_seed_used": 1234567890,
  "scenes": [
    {
      "scene_index": 0,
      "scene_prompt": "A young girl sitting by a window...",
      "method_used": "img2img",
      "images": ["base64_encoded_image_data"]
    },
    {
      "scene_index": 1,
      "scene_prompt": "The same girl walking through...",
      "method_used": "img2img", 
      "images": ["base64_encoded_image_data"]
    }
  ],
  "story_config": {
    "story_style": "picture_book",
    "character_strength": 0.65
  }
}
```

### Single Scene Response

```json
{
  "images": ["base64_encoded_image_data"],
  "method_used": "txt2img",
  "story_config": {
    "story_style": "picture_book"
  }
}
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `HUGGINGFACE_TOKEN` | HuggingFace token for downloading LoRA models | Yes |

---

## Deployment

### Build and Deploy

```bash
# Build the Docker image
docker build -t your-username/story-worker:latest .

# Push to registry
docker push your-username/story-worker:latest
```

### RunPod Configuration

- **GPU**: RTX 4090 or A100 recommended for optimal performance
- **Container Disk**: 25GB minimum (for higher resolution images and LoRA models)
- **Memory**: 16GB+ recommended
- **Environment Variables**: Set `HUGGINGFACE_TOKEN`

---

## Integration with vertelmoment.nl

This worker is designed to integrate with the **vertelmoment.nl** Next.js application:

1. The Next.js app collects story prompts and character references from users
2. API routes in the Next.js app call this RunPod worker with scene arrays
3. The worker returns consistent, print-ready story illustrations
4. The Next.js app processes and presents the complete story to users

### Example Next.js Integration

```typescript
// In your Next.js API route
const storyRequest = {
  scene_prompts: userStoryScenes,
  reference_images: userCharacterImages,
  story_style: userSelectedStyle,
  story_id: generateUniqueId(),
  width: 768,
  height: 768
};

const response = await fetch(RUNPOD_ENDPOINT, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${RUNPOD_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ input: storyRequest })
});
```

---

## Testing

Use the included test script to verify functionality:

```bash
# Update the script with your RunPod credentials
python test_story_generation.py
```

The test script verifies:
- ✅ Service status and available features
- ✅ Single scene generation (backward compatibility)
- ✅ Story batch generation with multiple scenes
- ✅ Style consistency across scenes

---

## Changelog

### v2.0.0 - Story Generation Update
- **Added**: Batch story generation with multiple scene prompts
- **Added**: Character consistency via reference image processing
- **Added**: Style consistency via seed locking per story
- **Added**: 8 pre-configured story style LoRAs
- **Enhanced**: Resolution increased to 768x768 for print quality
- **Enhanced**: Optimized settings for storybook creation
- **Maintained**: Full backward compatibility with existing API

### v1.0.0 - Initial Release
- Basic Automatic1111 WebUI integration
- Single image txt2img generation
- Deliberate v6 model included
