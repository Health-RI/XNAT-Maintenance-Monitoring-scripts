FROM python:3.11.15-alpine3.23

# Create a non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies as root (needed for pip install)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/xnat_maintenance_monitoring_scripts/ ./scripts/
COPY entrypoint.py ./

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Prepare the crontab spool directory so the non-root user can schedule its own cron jobs.
# /var/spool/cron/crontabs is a symlink to /etc/crontabs in this base image; chown the real
# target too since `chown -R` does not follow symlinks out of the tree it's walking.
RUN mkdir -p /var/spool/cron/crontabs && \
    chown -R appuser:appgroup /var/spool/cron /etc/crontabs

# Switch to the non-root user
USER appuser

ENTRYPOINT ["python", "entrypoint.py"]