# Steganography Mode Implementation Plan

## Goal
Add a new **Steganography Mode** to Encipherr that can hide an AES-encrypted text payload inside a PNG image, then extract it later without breaking the image file.

This plan is intentionally conservative: it reuses the existing encryption/key logic, keeps the current file encryption flow untouched, and adds the new feature behind a separate UI path.

## Scope

### In scope
- PNG-only steganography for now.
- AES-encrypt the payload before embedding it into the image.
- Capacity checks before writing anything.
- Clear validation errors for unsupported files, missing key, empty payload, and insufficient capacity.
- A new UI page for steganography that follows the current visual style.
- Return the generated stego image to the user after successful embedding.
- Extraction flow for PNG images that contain a hidden payload.

### Out of scope for the first pass
- Audio steganography.
- JPEG or other lossy image formats.
- Automatic resizing or recompression of the source image.
- Complex multi-file or batch steganography.
- Large refactors of the existing encryption routes.

## Design Principles
- Keep the current codebase stable by minimizing changes to existing routes and helpers.
- Reuse the current key field, key type selector, and text area patterns where possible.
- Follow the app’s current minimalistic UI and color style.
- Fail safely with explicit validation instead of trying to recover silently.
- Keep the original image untouched and generate a new output image.

## Recommended Technical Approach

### Embedding strategy
- Use an LSB-based approach for PNG images.
- Add a small payload header before the encrypted bytes.
- Header should include:
  - a magic marker to detect Encipherr stego payloads,
  - a version number,
  - payload length,
  - checksum or hash for integrity verification.

### Library choice
- Use `Pillow` (compatible with the chosen stego library, currently `12.2.0+`) for PNG image loading, validation, and pixel access.
- Use `stegano` for the LSB steganography encode/decode layer.
- Keep the steganography logic isolated behind one helper module so the route layer stays thin and the library can be swapped later if needed.
- Use Python's built-in `hashlib` for checksum or integrity validation instead of adding another dependency.

### Payload flow
1. User enters text and a key.
2. The app encrypts the text using the existing AES/key logic.
3. The encrypted payload is packed with the header.
4. The packed bytes are embedded into PNG pixel data using LSBs.
5. The new image is saved as a separate file and returned to the user.
6. For extraction, the app reverses the process and validates the header before decrypting.

## Validation Rules
- Accept only `.png` files.
- Reject empty text payloads.
- Reject missing key or invalid key format.
- Reject images that cannot fit the payload.
- Reject files that do not contain the Encipherr magic marker.
- Reject extraction if checksum or length validation fails.
- Return user-friendly error messages instead of raw tracebacks.

## File-Level Plan

### 1) Backend helpers
Add a small steganography helper in the existing module layer instead of building a separate subsystem.

Expected responsibilities:
- encode encrypted bytes into a PNG,
- decode bytes back from a PNG,
- validate capacity,
- validate header and checksum,
- raise clear exceptions for user-facing errors.

### 2) Route handling
Extend the existing `/home` POST handling with two additional branches:
- `Hide in Image`
- `Extract from Image`

The current upload/encrypt/decrypt logic should remain unchanged.

### 3) Frontend page
Create a new steganography page that borrows the current form structure:
- key input,
- key type selector,
- textarea for payload text,
- file input restricted to PNG,
- action buttons for hide and extract,
- flash/error display area matching the current style.

### 4) Navbar
Add a new navbar entry for the steganography page so it matches the existing page navigation pattern.

### 5) Dependencies
Add the minimum additional dependencies:
- `Pillow`
- `stegano`

Keep encryption on the existing `cryptography` package already used by the project.

## Suggested Implementation Order

### Phase 1: Safe plumbing
- Add the new page and navbar entry.
- Add route branches for steganography actions.
- Add frontend validation for PNG-only uploads.

### Phase 2: Encode path
- Encrypt text first using the existing AES path.
- Embed encrypted bytes into the image using LSBs.
- Add capacity checks before embedding.
- Return a generated stego PNG.

### Phase 3: Extract path
- Read the PNG image.
- Detect and validate the stego header.
- Recover the encrypted payload.
- Decrypt the payload using the existing key logic.

### Phase 4: Hardening
- Add checksum validation.
- Add clear exceptions for malformed inputs.
- Verify cleanup and file handling paths.
- Test success and failure cases.

## Error Handling Expectations
Every user-facing failure should map to a clear message, for example:
- unsupported file type,
- missing key,
- missing text,
- payload too large for the selected image,
- invalid or corrupted stego image,
- decryption failure due to wrong key.

Avoid letting these cases become 500 errors.

## UI Notes
- Keep the existing typography, spacing, and button style.
- Reuse the current card-and-form layout where practical.
- Keep the page visually consistent with the rest of the app.
- Do not introduce a heavy redesign for this feature.

## Safety Notes
- Do not modify the original image in place.
- Do not support lossy formats in v1.
- Do not silently resize or compress images.
- Keep the new logic isolated so existing file encryption behavior stays stable.

## Acceptance Criteria
- A user can hide AES-encrypted text inside a PNG image and download the stego image.
- A user can later extract the hidden payload from a valid stego PNG.
- Invalid inputs are handled gracefully with clear messages.
- The current encryption and file upload features continue to work unchanged.
- The UI stays consistent with the current Encipherr style.

## Notes For Review Before Coding
- Confirm the preferred steganography library.
- Confirm whether extraction should live on the same page or a separate page.
- Confirm whether the hidden payload should be text-only for v1 or also support file payloads later.
