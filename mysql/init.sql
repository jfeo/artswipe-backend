CREATE TABLE swipes (
	user_uuid CHAR(64),
	asset_id CHAR(64),
	choice CHAR(10),
	PRIMARY KEY (user_uuid, asset_id)
);
