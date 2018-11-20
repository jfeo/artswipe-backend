CREATE TABLE swipes (
	user_uuid CHAR(64),
	asset_id CHAR(64),
	choice CHAR(10),
	PRIMARY KEY (user_uuid, asset_id)
);

CREATE TABLE assets (
	id CHAR(64),
	title TEXT,
	thumb CHAR(128),
	upvotes INT,
	downvotes INT,
	PRIMARY KEY (id)
);
