# Media assets for the README

Drop these files here (exact filenames — the root `README.md` references them):

| File | What to capture | Recommended |
| --- | --- | --- |
| `demo.gif` | ~15–25s screen recording: type a question in the workspace → watch the agent steps stream → cited answer with the faithfulness bar. | 1280×720, < 10 MB (GitHub caps at 10 MB/file). Also export an `.mp4` for LinkedIn. |
| `workspace.png` | The workspace with a cited answer, route badge, and faithfulness bar visible. | 1600px wide, PNG |
| `dashboard.png` | The ticker dashboard with a live price chart + earnings (add an `FMP_API_KEY` first so charts render). | 1600px wide, PNG |

## How to record the GIF (macOS)

1. **Record**: `Cmd+Shift+5` → record a screen region of the browser → save the `.mov`.
2. **Convert to a lean GIF** (needs `ffmpeg` — `brew install ffmpeg`):
   ```bash
   ffmpeg -i demo.mov -vf "fps=12,scale=1280:-1:flags=lanczos" -loop 0 demo.gif
   ```
3. **Also make an MP4 for LinkedIn** (native video ranks higher than GIF):
   ```bash
   ffmpeg -i demo.mov -vf "scale=1280:-2" -c:v libx264 -pix_fmt yuv420p -movflags +faststart demo.mp4
   ```

## Committing

```bash
git add docs/media/demo.gif docs/media/workspace.png docs/media/dashboard.png
git commit -m "docs: add demo media"
git push
```

GitHub renders images and GIFs inline in the README from these relative paths.
