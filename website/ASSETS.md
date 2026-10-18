# Editorial website assets

The imagery in `dist/assets/collection/` is original AI-generated sample imagery, created with the built-in image-generation tool for this website. It depicts a fictional Crumble sample collection, not a retailer's products, real model results or factory observations. The generated PNG originals remain in the image-generation output directory; the project uses WebP encodings for delivery.

Files: `reference.webp`, `long.webp`, `pockets.webp`, `combined.webp`, `editorial-hero.webp`.

The four product images illustrate explicit sleeve/pocket controls. They are not evidence that a vision model detected those details. The editorial model is fictional.

The self-hosted Manrope font is unmodified, sourced from the Google Fonts repository. Its SIL Open Font License and copyright notice are in `dist/assets/fonts/OFL.txt`.

## Generation prompts

### base

Use case: product-mockup. Asset type: one original fashion e-commerce photograph for the Project Crumble garment-comparison demo. A front-facing ivory linen midi dress on an invisible ghost mannequin, square neckline, SHORT simple straight sleeves ending above the elbow, gently fitted waist seam, relaxed A-line skirt, NO pockets, no belt, no buttons. The entire dress from neckline to hem is visible, centered, straight-on with symmetrical sleeves. Premium realistic linen weave and natural fabric folds, excellent garment construction, soft studio daylight, clean light warm grey background, subtle shadow, refined contemporary retailer photography. Portrait 4:5 composition with generous even margins. Garment only: no person, no mannequin visible, no hanger, no accessories, no text, no logos, no watermark. This is an original fictional sample garment, not a replica of any brand. Keep the silhouette simple so it can be compared with a later long-sleeve patch-pocket variant.

### long

Edit target: the referenced original ivory linen square-neck midi dress product photograph. Change ONLY the short sleeves into full-length straight sleeves with narrow simple cuffs. Keep NO pockets. Preserve the exact garment body silhouette, square neckline, waist seam, A-line skirt, fabric texture and colour, garment proportions, camera position, studio lighting, light grey background and crop. Keep the whole dress visible with even margins. Realistic premium fashion e-commerce photography. No person, no hanger, no logos, no text or watermarks. All unrequested details must stay unchanged.

### pockets

Edit target: the referenced original ivory linen square-neck midi dress product photograph. Keep the SHORT sleeves exactly unchanged. Add exactly two neat matching ivory rectangular patch pockets on the front, one on each upper hip, symmetrical. No flaps or buttons. Preserve the exact garment body silhouette, square neckline, waist seam, A-line skirt, fabric texture and colour, garment proportions, camera position, studio lighting, light grey background and crop. Keep the whole dress visible with even margins. Realistic premium fashion e-commerce photography. No person, no hanger, no logos, no text or watermarks. All unrequested details must stay unchanged.

### combined

Edit target: the referenced original ivory linen square-neck midi dress product photograph. Change ONLY the short sleeves into full-length straight sleeves with narrow simple cuffs AND add exactly two neat matching ivory rectangular patch pockets, one on each upper hip, symmetrical, no flaps or buttons. Preserve the exact garment body silhouette, square neckline, waist seam, A-line skirt, fabric texture and colour, garment proportions, camera position, studio lighting, light grey background and crop. Keep the whole dress visible with even margins. Realistic premium fashion e-commerce photography. No person, no hanger, no logos, no text or watermarks. All unrequested details must stay unchanged.

### hero

Use case: photorealistic-natural / fashion editorial. Asset type: a premium editorial campaign photograph for the open-source garment intelligence project Crumble. Use the ivory linen square-neck short-sleeve midi dress in the reference as the garment wardrobe reference; make a NEW photograph, not a product cutout. A fictional adult female fashion model with medium brown skin and dark hair simply tied back wears this exact understated ivory linen dress in a minimal architectural daylight studio with warm grey plaster walls and a pale concrete floor. Full body, quiet natural standing/walking pose, face three-quarter angle, composed self-assured expression, flat minimal tan sandals, no accessories or props. Sophisticated independent fashion magazine photography, tactile fabric, warm natural sunlight from left casting soft sculptural architectural shadows, realistic proportions and skin texture, restrained neutral palette of ivory, stone and charcoal. Wide landscape 3:2 composition, model positioned in right half, negative space and gentle plaster-wall shadows on left, entire garment and hem visible. Photography must feel credible, refined and contemporary. NO text, no typography, no branding, no logos, no watermark, no user interface, no collage.
