run:
	python3 -m raspberrydeck.cli

deps:
	pip3 install -r requirements.txt

linuxsetup:
	sudo usermod -a -G plugdev `whoami`

	sudo tee /etc/udev/rules.d/99-streamdeck.rules << EOF
		SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="0060", MODE:="666", GROUP="plugdev"
		SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="0063", MODE:="666", GROUP="plugdev"
		SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="006c", MODE:="666", GROUP="plugdev"
		SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="006d", MODE:="666", GROUP="plugdev"
	EOF

	sudo udevadm control --reload-rules

	echo "Unplug and replug in device for the new udev rules to take effect"