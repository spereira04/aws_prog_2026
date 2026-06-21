FROM grafana/grafana:latest

ENV GF_USERS_ALLOW_SIGN_UP=false
# Copy data source provisioning configurations with correct ownership
COPY provisioning /etc/grafana/provisioning

# Copy dashboard JSON files with correct ownership
COPY dashboards/ /etc/grafana/dashboards/
