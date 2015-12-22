BASE_DIR         = $(shell pwd)
PACKAGE_VERSION ?= 0.3.0
BUILD_DIR       ?= $(BASE_DIR)/_build
export PROJECT_BASE    ?= riak-mesos
export DEPLOY_BASE     ?= riak-tools/$(PROJECT_BASE)

.PHONY: all clean package sync

all: clean package
clean:
	rm -rf $(BUILD_DIR)

### CLI Package begin
.PHONY: package_cli sync_cli
package: package_cli
package_cli: $(BUILD_DIR)/riak-mesos-cli-$(PACKAGE_VERSION).tar.gz
$(BUILD_DIR)/riak-mesos-cli-$(PACKAGE_VERSION).tar.gz:
	-rm -rf $(BUILD_DIR)/riak_mesos_cli
	mkdir -p $(BUILD_DIR)/riak_mesos_cli
	cp -R bin $(BUILD_DIR)/riak_mesos_cli/
	cp -R config $(BUILD_DIR)/riak_mesos_cli/
	echo "Thank you for downloading Riak Mesos Framework CLI tools. Run './bin/riak-mesos --help' to get started. Please visit https://github.com/basho-labs/riak-mesos-tools for usage information." > $(BUILD_DIR)/riak_mesos_cli/INSTALL.txt
	cd $(BUILD_DIR) && tar -zcvf riak_mesos_cli_$(PACKAGE_VERSION).tar.gz riak_mesos_cli
sync: sync_cli
sync_cli:
	cd $(BUILD_DIR)/ && \
		s3cmd put --acl-public riak_mesos_cli_$(PACKAGE_VERSION).tar.gz s3://$(DEPLOY_BASE)/
### CLI Package end

### DCOS Package begin
.PHONY: package_dcos sync_dcos
package: package_dcos
package_dcos: $(BUILD_DIR)/dcos-riak-$(PACKAGE_VERSION).tar.gz
$(BUILD_DIR)/dcos-riak-$(PACKAGE_VERSION).tar.gz:
	-rm -rf $(BUILD_DIR)/dcos-riak-*
	mkdir -p $(BUILD_DIR)/
	cp -R dcos-riak $(BUILD_DIR)/dcos-riak-$(PACKAGE_VERSION)
	cp bin/riak-mesos.py $(BUILD_DIR)/dcos-riak-$(PACKAGE_VERSION)/dcos_riak/cli.py
	cp bin/zktool_linux_amd64 $(BUILD_DIR)/dcos-riak-$(PACKAGE_VERSION)/dcos_riak/
	cp bin/zktool_darwin_amd64 $(BUILD_DIR)/dcos-riak-$(PACKAGE_VERSION)/dcos_riak/
	cd $(BUILD_DIR) && tar -zcvf dcos-riak-$(PACKAGE_VERSION).tar.gz dcos-riak-$(PACKAGE_VERSION)
sync: sync_dcos
sync_dcos:
	cd $(BUILD_DIR)/ && \
		s3cmd put --acl-public dcos-riak-$(PACKAGE_VERSION).tar.gz s3://$(DEPLOY_BASE)/
### DCOS Package end

### DCOS Repository Package begin
.PHONY: package_repo sync_repo
package: package_repo
package_repo: $(BUILD_DIR)/dcos-repo-$(PACKAGE_VERSION).zip
$(BUILD_DIR)/dcos-repo-$(PACKAGE_VERSION).zip:
	-rm -rf $(BUILD_DIR)/dcos-repo-*
	mkdir -p $(BUILD_DIR)/
	git clone https://github.com/mesosphere/universe.git $(BUILD_DIR)/dcos-repo-$(PACKAGE_VERSION)
	rm -rf $(BUILD_DIR)/dcos-repo-$(PACKAGE_VERSION)/.git
	cp -R dcos-repo/* $(BUILD_DIR)/dcos-repo-$(PACKAGE_VERSION)/repo/
	cd $(BUILD_DIR) && zip -r dcos-repo-$(PACKAGE_VERSION).zip dcos-repo-$(PACKAGE_VERSION)
sync: sync_repo
sync_repo:
	cd $(BUILD_DIR)/ && \
		s3cmd put --acl-public dcos-repo-$(PACKAGE_VERSION).zip s3://$(DEPLOY_BASE)/
### DCOS Repository Package end
