CREATE TABLE `message_tracking` (
  `raid_id` int NOT NULL,
  `chat_id` bigint NOT NULL,
  `message_id` int NOT NULL,
  `created` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`raid_id`,`chat_id`,`message_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `participation_types` (
  `participation_type_id` int NOT NULL,
  `participation_type` varchar(45) NOT NULL,
  `participation_max` int NOT NULL,
  PRIMARY KEY (`participation_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `raid_comments` (
  `comment_id` int NOT NULL,
  `raid_id` int NOT NULL,
  `username` varchar(96) NOT NULL,
  `comment` varchar(600) NOT NULL,
  `created` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`comment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `raiders` (
  `telegram_id` int NOT NULL,
  `username` varchar(64) NOT NULL,
  `nickname` varchar(64) DEFAULT NULL,
  `level` int DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  `created` datetime DEFAULT CURRENT_TIMESTAMP,
  `modified` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`telegram_id`),
  UNIQUE KEY `nickname_UNIQUE` (`nickname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `raid_participants` (
  `raid_id` int NOT NULL,
  `raider_id` int NOT NULL,
  `participation_type_id` int NOT NULL,
  `party_count` int NOT NULL DEFAULT '1',
  `created` datetime DEFAULT CURRENT_TIMESTAMP,
  `modified` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`raid_id`,`raider_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `raids` (
  `raid_id` int NOT NULL AUTO_INCREMENT,
  `raid_creator_id` int NOT NULL,
  `raid_datetime` datetime NOT NULL,
  `raid_title` varchar(150) NOT NULL,
  `raid_location` varchar(150) NOT NULL,
  `created` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `cancelled` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`raid_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `teams` (
  `team_id` int NOT NULL,
  `team_name` varchar(45) NOT NULL,
  `team_symbol` varchar(45) NOT NULL,
  PRIMARY KEY (`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `gyms` (
  `gym_id` int NOT NULL AUTO_INCREMENT,
  `gym_name` varchar(100) NOT NULL,
  `latitude` decimal(10,8) NOT NULL,
  `longitude` decimal(11,8) NOT NULL,
  PRIMARY KEY (`gym_id`),
  UNIQUE KEY `gym_id_UNIQUE` (`gym_id`),
  UNIQUE KEY `gym_name_UNIQUE` (`gym_name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE `gym_alias` (
  `gym_alias_id` int NOT NULL AUTO_INCREMENT,
  `gym_alias` varchar(100) NOT NULL,
  `gym_id` int NOT NULL,
  PRIMARY KEY (`gym_alias_id`),
  UNIQUE KEY `gym_alias_id_UNIQUE` (`gym_alias_id`),
  UNIQUE KEY `gym_alias_UNIQUE` (`gym_alias`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE 
    ALGORITHM = UNDEFINED 
    DEFINER = `admin`@`%` 
    SQL SECURITY DEFINER
VIEW `vw_raiders` AS
    SELECT 
        `raid_participants`.`raid_id` AS `raid_id`,
        `raid_participants`.`raider_id` AS `raider_id`,
        `raiders`.`username` AS `username`,
        `raiders`.`nickname` AS `nickname`,
        `raiders`.`level` AS `level`,
        `raiders`.`team_id` AS `team_id`,
        `teams`.`team_name` AS `team_name`,
        `teams`.`team_symbol` AS `team_symbol`,
        `raid_participants`.`participation_type_id` AS `participation_type_id`,
        `raid_participants`.`created` AS `participation_date`,
        `participation_types`.`participation_type` AS `participation_type`,
        `raid_participants`.`party_count` AS `party_count`
    FROM
        (((`raid_participants`
        JOIN `raiders` ON ((`raid_participants`.`raider_id` = `raiders`.`telegram_id`)))
        JOIN `participation_types` ON ((`raid_participants`.`participation_type_id` = `participation_types`.`participation_type_id`)))
        LEFT JOIN `teams` ON ((`raiders`.`team_id` = `teams`.`team_id`)))
    ORDER BY `raid_participants`.`participation_type_id` , `raid_participants`.`created`;

CREATE 
    ALGORITHM = UNDEFINED 
    DEFINER = `admin`@`%` 
    SQL SECURITY DEFINER
VIEW `vw_raids` AS
    SELECT 
        `raids`.`raid_id` AS `raid_id`,
        `raids`.`raid_creator_id` AS `raid_creator_id`,
        `raids`.`raid_datetime` AS `raid_datetime`,
        `raids`.`raid_title` AS `raid_title`,
        `raids`.`raid_location` AS `raid_location`,
        `raids`.`cancelled` AS `cancelled`,
        `raiders`.`username` AS `raid_creator_username`,
        `raiders`.`nickname` AS `raid_creator_nickname`,
        `gyms`.`gym_name` AS `gym_name`,
        `gyms`.`latitude` AS `latitude`,
        `gyms`.`longitude` AS `longitude`
    FROM
        (((`raids`
        JOIN `raiders` ON ((`raiders`.`telegram_id` = `raids`.`raid_creator_id`)))
        LEFT JOIN `gym_alias` ON ((`gym_alias`.`gym_alias` LIKE `raids`.`raid_location`)))
        LEFT JOIN `gyms` ON ((`gyms`.`gym_id` = `gym_alias`.`gym_id`)))