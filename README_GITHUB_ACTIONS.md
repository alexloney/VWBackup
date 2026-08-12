# GitHub Actions - Docker Build & Publish

This repository includes GitHub Actions workflows to automatically build and publish Docker images to GitHub Container Registry (ghcr.io).

## 🚀 Workflows

### 1. **Build and Push Docker Image** (`.github/workflows/docker-publish.yml`)

Automatically builds and publishes Docker images when:
- **Pushing to `main`/`master` branch** → Tagged as `latest`
- **Creating version tags** (e.g., `v1.0.0`) → Tagged with version numbers
- **Manual trigger** → Via GitHub Actions UI

**Supported platforms:**
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM, Apple Silicon, Raspberry Pi)

### 2. **Test Docker Build** (`.github/workflows/docker-test.yml`)

Tests Docker builds on pull requests to ensure changes don't break the image.

## 📦 Using Pre-built Images

Instead of building locally, you can pull pre-built images from GitHub Container Registry:

### Pull the latest image:

```bash
docker pull ghcr.io/YOUR_USERNAME/vwbackup:latest
```

Replace `YOUR_USERNAME` with your GitHub username (lowercase).

### Run with docker-compose:

Update your `docker-compose.yml`:

```yaml
services:
  vw-backup:
    image: ghcr.io/YOUR_USERNAME/vwbackup:latest
    # Remove the 'build: .' line
    container_name: vaultwarden-backup
    # ... rest of configuration
```

Then run:

```bash
docker-compose pull  # Pull latest image
docker-compose up -d # Start container
```

## 🏷️ Image Tags

The workflow automatically creates the following tags:

| Trigger | Tag | Example |
|---------|-----|---------|
| Push to main/master | `latest` | `ghcr.io/user/vwbackup:latest` |
| Version tag | `1.0.0`, `1.0`, `1` | `ghcr.io/user/vwbackup:1.0.0` |
| Branch push | `branch-name` | `ghcr.io/user/vwbackup:develop` |
| Commit SHA | `branch-sha123456` | `ghcr.io/user/vwbackup:main-sha123456` |

### Using specific versions:

```bash
# Use latest
docker pull ghcr.io/YOUR_USERNAME/vwbackup:latest

# Use specific version
docker pull ghcr.io/YOUR_USERNAME/vwbackup:1.0.0

# Use major version (gets latest 1.x.x)
docker pull ghcr.io/YOUR_USERNAME/vwbackup:1
```

## 🔧 Setup Instructions

### 1. Enable GitHub Container Registry

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions. No additional secrets needed!

### 2. Make package public (optional)

By default, packages are private. To make them public:

1. Go to your repository on GitHub
2. Click on "Packages" (right side)
3. Click on your package (vwbackup)
4. Click "Package settings"
5. Scroll to "Danger Zone"
6. Click "Change visibility" → Select "Public"

### 3. Create a version tag (optional)

To trigger a versioned build:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This will create images tagged as:
- `ghcr.io/YOUR_USERNAME/vwbackup:1.0.0`
- `ghcr.io/YOUR_USERNAME/vwbackup:1.0`
- `ghcr.io/YOUR_USERNAME/vwbackup:1`
- `ghcr.io/YOUR_USERNAME/vwbackup:latest`

### 4. Manual trigger

You can manually trigger a build:

1. Go to "Actions" tab in your GitHub repository
2. Select "Build and Push Docker Image" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## 🔐 Pulling Private Images

If your package is private, you need to authenticate:

```bash
# Create a personal access token (PAT) with read:packages scope
# Go to: Settings → Developer settings → Personal access tokens → Tokens (classic)

# Login to ghcr.io
echo YOUR_PAT | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Pull the image
docker pull ghcr.io/YOUR_USERNAME/vwbackup:latest
```

**For docker-compose with private images:**

```bash
# Login first
docker login ghcr.io

# Then pull and run
docker-compose pull
docker-compose up -d
```

## 📊 Monitoring Builds

### View workflow runs:

1. Go to your repository on GitHub
2. Click "Actions" tab
3. View status of builds

### Check published packages:

1. Go to your GitHub profile
2. Click "Packages" tab
3. Click on "vwbackup" to see all versions

## 🛠️ Customization

### Change platforms

Edit `.github/workflows/docker-publish.yml`:

```yaml
platforms: linux/amd64  # Build only for x86_64
```

Or add more platforms:

```yaml
platforms: linux/amd64,linux/arm64,linux/arm/v7
```

### Change image name

The image name is automatically set to `ghcr.io/USERNAME/REPOSITORY_NAME`.

To use a custom name, edit the workflow:

```yaml
env:
  IMAGE_NAME: your-custom-name  # Instead of ${{ github.repository }}
```

### Add build arguments

To pass build arguments:

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    push: ${{ github.event_name != 'pull_request' }}
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
    build-args: |
      VERSION=${{ github.ref_name }}
      BUILD_DATE=${{ github.event.head_commit.timestamp }}
```

## 📝 Example: Complete Update Flow

```bash
# 1. Make changes to your code
git add .
git commit -m "Improve backup performance"

# 2. Push to main branch (triggers build of 'latest')
git push origin main

# 3. Create a version tag (triggers versioned build)
git tag v1.1.0
git push origin v1.1.0

# 4. Wait for GitHub Actions to complete (check Actions tab)

# 5. Pull and use the new image
docker pull ghcr.io/YOUR_USERNAME/vwbackup:latest
docker-compose up -d
```

## 🐛 Troubleshooting

### Build fails with permission error

Make sure your repository has Actions enabled:
- Go to Settings → Actions → General
- Enable "Allow all actions and reusable workflows"

### Can't pull image - permission denied

If package is private, authenticate first:
```bash
docker login ghcr.io
```

### Image not found

Check the exact image name:
- Go to your GitHub profile → Packages
- Copy the exact pull command shown there

### Build is slow

The workflow uses GitHub Actions cache to speed up builds. First build is slow, subsequent builds are faster.

## 🔄 Migration from Docker Hub

If you're currently using Docker Hub, the GitHub Container Registry offers:
- ✅ Free for public repositories
- ✅ Better integration with GitHub
- ✅ Automatic versioning from git tags
- ✅ Multi-platform builds
- ✅ Unlimited bandwidth for public images

To migrate, just update your docker-compose.yml to use `ghcr.io` instead of `docker.io`.
